"""边路由 - 支持多系统"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import List, Optional
from database import get_db, engine
from models import System
from schemas import EdgeCreate, EdgeUpdate, EdgeResponse, EdgeBatchCreate
from routers.nodes import get_node_table

router = APIRouter(prefix="/api/systems/{system_id}/edges", tags=["边管理"])


@router.get("", response_model=List[dict])
async def get_all_edges(system_id: int, db: Session = Depends(get_db)):
    """获取指定系统的所有边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    inspector = inspect(engine)
    edge_table_name = f"edges_system_{system_id}"
    if not inspector.has_table(edge_table_name):
        return []
    
    node_table = get_node_table(system_id)
    
    # 查询边
    edge_query = text(f"SELECT * FROM {edge_table_name}")
    edges_result = db.execute(edge_query)
    edge_rows = edges_result.fetchall()
    edge_columns = edges_result.keys()
    
    # 查询所有节点用于关联
    node_query = text(f"SELECT id, name, type FROM {node_table.name}")
    nodes_result = db.execute(node_query)
    nodes = {row[0]: {"id": row[0], "name": row[1], "type": row[2]} for row in nodes_result.fetchall()}
    
    edges = []
    for row in edge_rows:
        edge = dict(zip(edge_columns, row))
        edge['system_id'] = system_id
        
        # 添加源和目标节点信息
        edge['source_node'] = nodes.get(edge['source_id'])
        edge['target_node'] = nodes.get(edge['target_id'])
        
        # 转换 datetime
        if edge.get('created_at'):
            edge['created_at'] = edge['created_at'].isoformat() if hasattr(edge['created_at'], 'isoformat') else str(edge['created_at'])
        
        edges.append(edge)
    
    return edges


@router.get("/{edge_id}", response_model=dict)
async def get_edge(system_id: int, edge_id: int, db: Session = Depends(get_db)):
    """获取单个边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    inspector = inspect(engine)
    edge_table_name = f"edges_system_{system_id}"
    if not inspector.has_table(edge_table_name):
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 查询边
    query = text(f"SELECT * FROM {edge_table_name} WHERE id = :id")
    result = db.execute(query, {"id": edge_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    
    columns = result.keys()
    edge = dict(zip(columns, row))
    edge['system_id'] = system_id
    
    # 添加节点信息
    node_query = text(f"SELECT id, name, type FROM {node_table.name}")
    nodes_result = db.execute(node_query)
    nodes = {row[0]: {"id": row[0], "name": row[1], "type": row[2]} for row in nodes_result.fetchall()}
    
    edge['source_node'] = nodes.get(edge['source_id'])
    edge['target_node'] = nodes.get(edge['target_id'])
    
    return edge


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_edge(system_id: int, edge_data: EdgeCreate, db: Session = Depends(get_db)):
    """创建边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 检查源节点存在
    check_source = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
    source_exists = db.execute(check_source, {"id": edge_data.source_id}).fetchone()
    if not source_exists:
        raise HTTPException(status_code=400, detail=f"源节点 {edge_data.source_id} 不存在")
    
    # 检查目标节点存在
    check_target = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
    target_exists = db.execute(check_target, {"id": edge_data.target_id}).fetchone()
    if not target_exists:
        raise HTTPException(status_code=400, detail=f"目标节点 {edge_data.target_id} 不存在")
    
    # 检查自环
    if edge_data.source_id == edge_data.target_id:
        raise HTTPException(status_code=400, detail="不能创建自环边")
    
    # 检查重复边
    edge_table_name = f"edges_system_{system_id}"
    check_dup = text(f"""
        SELECT id FROM {edge_table_name} 
        WHERE source_id = :source_id AND target_id = :target_id
    """)
    dup_exists = db.execute(check_dup, {
        "source_id": edge_data.source_id,
        "target_id": edge_data.target_id
    }).fetchone()
    if dup_exists:
        raise HTTPException(status_code=400, detail="该边已存在")
    
    # 插入数据
    from datetime import datetime
    now = datetime.utcnow()
    
    insert_query = text(f"""
        INSERT INTO {edge_table_name} (source_id, target_id, weight, description, created_at)
        VALUES (:source_id, :target_id, :weight, :description, :created_at)
    """)
    
    result = db.execute(insert_query, {
        "source_id": edge_data.source_id,
        "target_id": edge_data.target_id,
        "weight": edge_data.weight,
        "description": edge_data.description,
        "created_at": now
    })
    db.commit()
    
    return await get_edge(system_id, result.lastrowid, db)


@router.put("/{edge_id}", response_model=dict)
async def update_edge(system_id: int, edge_id: int, edge_data: EdgeUpdate, db: Session = Depends(get_db)):
    """更新边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    inspector = inspect(engine)
    edge_table_name = f"edges_system_{system_id}"
    if not inspector.has_table(edge_table_name):
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 检查边存在
    check_query = text(f"SELECT * FROM {edge_table_name} WHERE id = :id")
    existing = db.execute(check_query, {"id": edge_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    
    update_data = edge_data.model_dump(exclude_unset=True)
    if not update_data:
        return await get_edge(system_id, edge_id, db)
    
    # 验证节点
    if "source_id" in update_data:
        check_source = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
        if not db.execute(check_source, {"id": update_data["source_id"]}).fetchone():
            raise HTTPException(status_code=400, detail=f"源节点 {update_data['source_id']} 不存在")
    
    if "target_id" in update_data:
        check_target = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
        if not db.execute(check_target, {"id": update_data["target_id"]}).fetchone():
            raise HTTPException(status_code=400, detail=f"目标节点 {update_data['target_id']} 不存在")
    
    # 检查自环
    source_id = update_data.get("source_id", existing[1])
    target_id = update_data.get("target_id", existing[2])
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="不能创建自环边")
    
    # 构建更新语句
    set_clauses = []
    params = {"id": edge_id}
    for key, value in update_data.items():
        set_clauses.append(f"{key} = :{key}")
        params[key] = value
    
    update_query = text(f"""
        UPDATE {edge_table_name} 
        SET {', '.join(set_clauses)}
        WHERE id = :id
    """)
    
    db.execute(update_query, params)
    db.commit()
    
    return await get_edge(system_id, edge_id, db)




@router.delete("/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_edges(system_id: int, db: Session = Depends(get_db)):
    """删除指定系统的所有边"""
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")

    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    if inspector.has_table(edge_table_name):
        db.execute(text(f"DELETE FROM {edge_table_name}"))
        db.commit()

    return None


@router.post("/auto-init", response_model=dict)
async def auto_init_edges(system_id: int, db: Session = Depends(get_db)):
    """
    自动初始化边关系
    
    规则:
    - 节点 → 系统 (weight=8): source=节点, target=系统
    - 集群 → 节点 (weight=8): source=集群, target=节点
    - 服务器 → 集群 (weight=5): source=服务器, target=集群 (通过cluster字段=集群insertID)
    - 组件 → 服务器 (weight=10): source=组件, target=服务器 (通过cluster字段=服务器insertID)
    
    cluster 字段保存的是上级节点的 insertID，用于初始化边关系。
    不修改已存在的边（按source_id+target_id判断）。
    手动创建/修改边时不参考 cluster 字段。
    """
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")

    node_table = get_node_table(system_id)
    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    
    # 确保边表存在
    if not inspector.has_table(edge_table_name):
        db.execute(text(f"""
            CREATE TABLE {edge_table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                weight INTEGER DEFAULT 1,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_id, target_id)
            )
        """))
        db.commit()

    # 1. 查询所有节点
    node_query = text(f"SELECT id, name, type, cluster, insertID FROM {node_table.name}")
    nodes_result = db.execute(node_query)
    nodes = {}  # id -> node
    nodes_by_insert_id = {}  # insertID -> node
    for row in nodes_result.fetchall():
        node = {"id": row[0], "name": row[1], "type": row[2], "cluster": row[3], "insertID": row[4]}
        nodes[row[0]] = node
        if row[4]:  # insertID 不为空
            nodes_by_insert_id[row[4]] = node
    
    if not nodes:
        return {"message": "系统中没有节点", "created": 0, "skipped": 0, "total": 0}

    # 2. 查询已存在的边
    existing_edges_query = text(f"SELECT source_id, target_id FROM {edge_table_name}")
    existing_edges_result = db.execute(existing_edges_query)
    existing_edges = set()
    for row in existing_edges_result.fetchall():
        existing_edges.add((row[0], row[1]))

    # 3. 按类型分类节点
    system_nodes = [n for n in nodes.values() if n["type"] in ["系统", "系统功能"]]  # 不包含"服务系统"和"支撑系统"
    support_nodes = [n for n in nodes.values() if n["type"] == "支撑系统"]  # 不与节点生成边
    service_nodes = [n for n in nodes.values() if n["type"] == "服务系统"]  # 不与节点生成边
    node_nodes = [n for n in nodes.values() if n["type"] == "节点"]
    cluster_nodes = [n for n in nodes.values() if n["type"] == "集群"]
    server_nodes = [n for n in nodes.values() if n["type"] == "服务器"]
    component_nodes = [n for n in nodes.values() if n["type"] == "组件"]

    # 4. 构建待创建的边
    edges_to_create = []
    
    # 节点 → 系统 (weight=8): 通过 cluster 字段(存的是上级系统的 insertID) 查找
    for node in node_nodes:
        if node["cluster"]:  # cluster 存的是上级系统的 insertID
            target_sys = nodes_by_insert_id.get(node["cluster"])
            if target_sys and target_sys["type"] in ["系统", "系统功能"]:
                if (node["id"], target_sys["id"]) not in existing_edges:
                    edges_to_create.append({
                        "source_id": node["id"],
                        "target_id": target_sys["id"],
                        "weight": 8,
                        "description": f"{node['name']} 依赖 {target_sys['name']}"
                    })
    
    # 集群 → 节点 (weight=8): 通过 cluster 字段(存的是上级节点的 insertID) 查找
    for cluster in cluster_nodes:
        if cluster["cluster"]:  # cluster 存的是上级节点的 insertID
            target_node = nodes_by_insert_id.get(cluster["cluster"])
            if target_node and target_node["type"] == "节点":
                if (cluster["id"], target_node["id"]) not in existing_edges:
                    edges_to_create.append({
                        "source_id": cluster["id"],
                        "target_id": target_node["id"],
                        "weight": 8,
                        "description": f"{cluster['name']} 依赖 {target_node['name']}"
                    })
    
    # 服务器 → 集群 (weight=5): 通过 cluster 字段(存的是上级集群的 insertID) 查找
    for server in server_nodes:
        if server["cluster"]:  # cluster 存的是上级集群的 insertID
            target_cluster = nodes_by_insert_id.get(server["cluster"])
            if target_cluster and target_cluster["type"] == "集群":
                if (server["id"], target_cluster["id"]) not in existing_edges:
                    edges_to_create.append({
                        "source_id": server["id"],
                        "target_id": target_cluster["id"],
                        "weight": 5,
                        "description": f"{server['name']} 依赖 {target_cluster['name']}"
                    })
    
    # 组件 → 服务器 (weight=10): 通过 cluster 字段(存的是上级服务器的 insertID) 查找
    for component in component_nodes:
        if component["cluster"]:  # cluster 存的是上级服务器的 insertID
            target_server = nodes_by_insert_id.get(component["cluster"])
            if target_server and target_server["type"] == "服务器":
                if (component["id"], target_server["id"]) not in existing_edges:
                    edges_to_create.append({
                        "source_id": component["id"],
                        "target_id": target_server["id"],
                        "weight": 10,
                        "description": f"{component['name']} 依赖 {target_server['name']}"
                    })

    # 5. 批量插入边
    from datetime import datetime
    now = datetime.utcnow()
    created_count = 0
    
    for edge in edges_to_create:
        try:
            insert_query = text(f"""
                INSERT INTO {edge_table_name} (source_id, target_id, weight, description, created_at)
                VALUES (:source_id, :target_id, :weight, :description, :created_at)
            """)
            db.execute(insert_query, {
                "source_id": edge["source_id"],
                "target_id": edge["target_id"],
                "weight": edge["weight"],
                "description": edge["description"],
                "created_at": now
            })
            db.commit()
            created_count += 1
        except Exception as e:
            db.rollback()
            # 可能是UNIQUE约束冲突，忽略
            continue

    return {
        "message": f"自动初始化完成",
        "created": created_count,
        "skipped": len(edges_to_create) - created_count,
        "total": len(edges_to_create),
        "details": {
            "节点→系统": len([e for e in edges_to_create if e["weight"] == 8 and 
                      any(nodes[e["source_id"]]["type"] == "节点" for _ in [1])]),
            "集群→节点": len([e for e in edges_to_create if e["weight"] == 8 and 
                       any(nodes[e["source_id"]]["type"] == "集群" for _ in [1])]),
            "服务器→集群": len([e for e in edges_to_create if e["weight"] == 5]),
            "组件→服务器": len([e for e in edges_to_create if e["weight"] == 10])
        }
    }


@router.delete("/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(system_id: int, edge_id: int, db: Session = Depends(get_db)):
    """删除边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")

    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    if not inspector.has_table(edge_table_name):
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    check_query = text(f"SELECT id FROM {edge_table_name} WHERE id = :id")
    existing = db.execute(check_query, {"id": edge_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")

    # 删除
    delete_query = text(f"DELETE FROM {edge_table_name} WHERE id = :id")
    db.execute(delete_query, {"id": edge_id})
    db.commit()

    return None
    """删除边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    if not inspector.has_table(edge_table_name):
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    check_query = text(f"SELECT id FROM {edge_table_name} WHERE id = :id")
    existing = db.execute(check_query, {"id": edge_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"边 {edge_id} 不存在")
    
    # 删除
    delete_query = text(f"DELETE FROM {edge_table_name} WHERE id = :id")
    db.execute(delete_query, {"id": edge_id})
    db.commit()
    
    return None


@router.get("/from/{node_id}", response_model=List[dict])
async def get_edges_from_node(system_id: int, node_id: int, db: Session = Depends(get_db)):
    """获取从某节点出发的所有边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    if not inspector.has_table(edge_table_name):
        return []
    
    query = text(f"SELECT * FROM {edge_table_name} WHERE source_id = :node_id")
    result = db.execute(query, {"node_id": node_id})
    
    edges = []
    for row in result.fetchall():
        edge = dict(zip(result.keys(), row))
        edge['system_id'] = system_id
        edges.append(edge)
    
    return edges


@router.get("/to/{node_id}", response_model=List[dict])
async def get_edges_to_node(system_id: int, node_id: int, db: Session = Depends(get_db)):
    """获取指向某节点的所有边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    edge_table_name = f"edges_system_{system_id}"
    inspector = inspect(engine)
    if not inspector.has_table(edge_table_name):
        return []
    
    query = text(f"SELECT * FROM {edge_table_name} WHERE target_id = :node_id")
    result = db.execute(query, {"node_id": node_id})
    
    edges = []
    for row in result.fetchall():
        edge = dict(zip(result.keys(), row))
        edge['system_id'] = system_id
        edges.append(edge)
    
    return edges


@router.post("/batch", response_model=List[dict], status_code=status.HTTP_201_CREATED)
async def batch_create_edges(system_id: int, batch_data: EdgeBatchCreate, db: Session = Depends(get_db)):
    """批量创建边"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    edge_table_name = f"edges_system_{system_id}"
    
    created_edges = []
    errors = []
    
    from datetime import datetime
    now = datetime.utcnow()
    
    for i, edge_data in enumerate(batch_data.edges):
        try:
            # 检查源节点
            check_source = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
            if not db.execute(check_source, {"id": edge_data.source_id}).fetchone():
                errors.append(f"第 {i+1} 行: 源节点 {edge_data.source_id} 不存在")
                continue
            
            # 检查目标节点
            check_target = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
            if not db.execute(check_target, {"id": edge_data.target_id}).fetchone():
                errors.append(f"第 {i+1} 行: 目标节点 {edge_data.target_id} 不存在")
                continue
            
            # 检查自环
            if edge_data.source_id == edge_data.target_id:
                errors.append(f"第 {i+1} 行: 不能创建自环边")
                continue
            
            # 检查重复
            check_dup = text(f"""
                SELECT id FROM {edge_table_name} 
                WHERE source_id = :source_id AND target_id = :target_id
            """)
            if db.execute(check_dup, {
                "source_id": edge_data.source_id,
                "target_id": edge_data.target_id
            }).fetchone():
                errors.append(f"第 {i+1} 行: 该边已存在")
                continue
            
            # 插入
            insert_query = text(f"""
                INSERT INTO {edge_table_name} (source_id, target_id, weight, description, created_at)
                VALUES (:source_id, :target_id, :weight, :description, :created_at)
            """)
            
            result = db.execute(insert_query, {
                "source_id": edge_data.source_id,
                "target_id": edge_data.target_id,
                "weight": edge_data.weight,
                "description": edge_data.description,
                "created_at": now
            })
            db.commit()
            
            created_edges.append(await get_edge(system_id, result.lastrowid, db))
        except Exception as e:
            db.rollback()
            errors.append(f"第 {i+1} 行: {str(e)}")
    
    if errors and not created_edges:
        raise HTTPException(status_code=400, detail=f"批量创建失败: {'; '.join(errors)}")
    
    return created_edges
