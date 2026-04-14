"""节点路由 - 支持多系统"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import List, Optional
from database import get_db
from models import System
from schemas import NodeCreate, NodeUpdate, NodeResponse, NodeBatchCreate, NodeBatchResponse

router = APIRouter(prefix="/api/systems/{system_id}/nodes", tags=["节点管理"])

# 节点类型列表
NODE_TYPES = [
    "服务系统",
    "系统功能",
    "系统",
    "支撑系统",
    "节点",
    "集群",
    "服务器",
    "组件"
]


def get_node_table(system_id: int):
    """获取指定系统的节点表"""
    from database import engine
    from sqlalchemy import Table, MetaData
    
    inspector = inspect(engine)
    table_name = f"nodes_system_{system_id}"
    
    if not inspector.has_table(table_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"系统 {system_id} 不存在"
        )
    
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    return metadata.tables[table_name]


def get_edge_table(system_id: int):
    """获取指定系统的边表"""
    from database import engine
    from sqlalchemy import Table, MetaData
    
    inspector = inspect(engine)
    table_name = f"edges_system_{system_id}"
    
    if not inspector.has_table(table_name):
        return None
    
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    return metadata.tables[table_name]


@router.get("/types", response_model=List[str])
async def get_node_types(system_id: int, db: Session = Depends(get_db)):
    """获取所有节点类型"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    return NODE_TYPES


@router.get("", response_model=List[dict])
async def get_all_nodes(system_id: int, node_type: Optional[str] = None, 
                        db: Session = Depends(get_db)):
    """获取指定系统的所有节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 查询字段（包含 insertID，用于导出功能）
    select_columns = "id, name, type, description, cluster, insertID, properties, created_at, updated_at"
    
    # 构建查询
    if node_type:
        query = text(f"SELECT {select_columns} FROM {node_table.name} WHERE type = :type ORDER BY type, name")
        result = db.execute(query, {"type": node_type})
    else:
        query = text(f"SELECT {select_columns} FROM {node_table.name} ORDER BY type, name")
        result = db.execute(query)
    
    rows = result.fetchall()
    columns = result.keys()
    
    nodes = []
    for row in rows:
        node = dict(zip(columns, row))
        node['system_id'] = system_id
        # 转换 datetime
        if node.get('created_at'):
            node['created_at'] = node['created_at'].isoformat() if hasattr(node['created_at'], 'isoformat') else str(node['created_at'])
        if node.get('updated_at'):
            node['updated_at'] = node['updated_at'].isoformat() if hasattr(node['updated_at'], 'isoformat') else str(node['updated_at'])
        nodes.append(node)
    
    return nodes


@router.get("/{node_id}", response_model=dict)
async def get_node(system_id: int, node_id: int, db: Session = Depends(get_db)):
    """获取单个节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 查询字段（包含 insertID）
    select_columns = "id, name, type, description, cluster, insertID, properties, created_at, updated_at"
    query = text(f"SELECT {select_columns} FROM {node_table.name} WHERE id = :id")
    result = db.execute(query, {"id": node_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
    
    columns = result.keys()
    node = dict(zip(columns, row))
    node['system_id'] = system_id
    return node


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_node(system_id: int, node_data: NodeCreate, db: Session = Depends(get_db)):
    """创建节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    # 验证类型
    if node_data.type not in NODE_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的节点类型: {node_data.type}")
    
    # 系统类节点不允许通过此接口添加（只有"系统"类型不能添加）
    if node_data.type == "系统":
        raise HTTPException(
            status_code=400, 
            detail=f"「系统」类型的节点不能通过此方式添加，请通过「添加系统」功能添加"
        )
    
    node_table = get_node_table(system_id)
    
    # 名称唯一性检查规则：
    # - 支撑系统、服务系统、系统功能、节点：相同type下name必须唯一
    # - 集群、服务器、组件：相同type下name可以重复
    unique_name_types = ["支撑系统", "服务系统", "系统功能", "节点"]
    if node_data.type in unique_name_types:
        check_query = text(f"SELECT id FROM {node_table.name} WHERE name = :name AND type = :type")
        existing = db.execute(check_query, {"name": node_data.name, "type": node_data.type}).fetchone()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"类型为「{node_data.type}」的节点，名称「{node_data.name}」已存在"
            )
    
    # 插入数据
    from datetime import datetime
    now = datetime.utcnow()
    
    insert_query = text(f"""
        INSERT INTO {node_table.name} (name, type, description, properties, created_at, updated_at)
        VALUES (:name, :type, :description, :properties, :created_at, :updated_at)
    """)
    
    result = db.execute(insert_query, {
        "name": node_data.name,
        "type": node_data.type,
        "description": node_data.description,
        "properties": str(node_data.properties) if node_data.properties else None,
        "created_at": now,
        "updated_at": now
    })
    db.commit()
    
    # 返回创建的节点
    return await get_node(system_id, result.lastrowid, db)


@router.put("/{node_id}", response_model=dict)
async def update_node(system_id: int, node_id: int, node_data: NodeUpdate, db: Session = Depends(get_db)):
    """更新节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    
    # 检查节点存在
    check_query = text(f"SELECT * FROM {node_table.name} WHERE id = :id")
    existing = db.execute(check_query, {"id": node_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
    
    update_data = node_data.model_dump(exclude_unset=True)
    if not update_data:
        return await get_node(system_id, node_id, db)
    
    # 检查重名
    if "name" in update_data:
        name_check = text(f"SELECT id FROM {node_table.name} WHERE name = :name AND id != :id")
        name_exists = db.execute(name_check, {"name": update_data["name"], "id": node_id}).fetchone()
        if name_exists:
            raise HTTPException(status_code=400, detail=f"节点名称 '{update_data['name']}' 已存在")
    
    # 验证类型
    if "type" in update_data and update_data["type"] not in NODE_TYPES:
        raise HTTPException(status_code=400, detail=f"无效的节点类型: {update_data['type']}")
    
    # 构建更新语句
    set_clauses = []
    params = {"id": node_id}
    for key, value in update_data.items():
        if key == "properties":
            set_clauses.append(f"{key} = :{key}")
            params[key] = str(value) if value else None
        else:
            set_clauses.append(f"{key} = :{key}")
            params[key] = value
    
    from datetime import datetime
    set_clauses.append("updated_at = :updated_at")
    params["updated_at"] = datetime.utcnow()
    
    update_query = text(f"""
        UPDATE {node_table.name} 
        SET {', '.join(set_clauses)}
        WHERE id = :id
    """)
    
    db.execute(update_query, params)
    db.commit()
    
    return await get_node(system_id, node_id, db)


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(system_id: int, node_id: int, db: Session = Depends(get_db)):
    """删除节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    edge_table = get_edge_table(system_id)
    
    # 检查节点存在
    check_query = text(f"SELECT id FROM {node_table.name} WHERE id = :id")
    existing = db.execute(check_query, {"id": node_id}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
    
    # 删除相关的边
    if edge_table is not None:
        delete_edges_query = text(f"""
            DELETE FROM {edge_table.name} 
            WHERE source_id = :node_id OR target_id = :node_id
        """)
        db.execute(delete_edges_query, {"node_id": node_id})
    
    # 删除节点
    delete_query = text(f"DELETE FROM {node_table.name} WHERE id = :id")
    db.execute(delete_query, {"id": node_id})
    db.commit()
    
    return None


@router.post("/batch", response_model=NodeBatchResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_nodes(system_id: int, batch_data: NodeBatchCreate, db: Session = Depends(get_db)):
    """
    批量创建/更新节点
    
    导入规则:
    - insertID 相同: 更新已有节点(保留id，按新数据更新name/type/description/cluster/properties)
    - insertID 不同或无insertID: 新增节点
    - 无 insertID 且名称冲突: 报错
    """
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail=f"系统 {system_id} 不存在")
    
    node_table = get_node_table(system_id)
    created_nodes = []
    updated_nodes = []
    errors = []
    
    from datetime import datetime
    now = datetime.utcnow()
    
    # 1. 构建 insertID → node_id 映射(用于快速查找)
    insert_id_query = text(f"SELECT id, insertID FROM {node_table.name} WHERE insertID IS NOT NULL AND insertID != ''")
    insert_id_result = db.execute(insert_id_query)
    insert_id_map = {row[1]: row[0] for row in insert_id_result.fetchall()}  # insertID -> node_id
    
    # 2. 构建名称 → node_id 映射(用于无insertID时的冲突检查)
    name_query = text(f"SELECT id, name FROM {node_table.name}")
    name_result = db.execute(name_query)
    name_map = {row[1]: row[0] for row in name_result.fetchall()}  # name -> node_id
    
    for i, node_data in enumerate(batch_data.nodes):
        try:
            node_insert_id = getattr(node_data, 'insertID', None) or None
            
            # 情况1: 有 insertID 且已存在 -> 更新
            if node_insert_id and node_insert_id in insert_id_map:
                existing_id = insert_id_map[node_insert_id]
                
                # 构建更新语句
                update_query = text(f"""
                    UPDATE {node_table.name}
                    SET name = :name, type = :type, description = :description, 
                        cluster = :cluster, properties = :properties, updated_at = :updated_at
                    WHERE id = :id
                """)
                db.execute(update_query, {
                    "id": existing_id,
                    "name": node_data.name,
                    "type": node_data.type,
                    "description": node_data.description,
                    "cluster": node_data.cluster,
                    "properties": str(node_data.properties) if node_data.properties else None,
                    "updated_at": now
                })
                db.commit()
                updated_nodes.append(await get_node(system_id, existing_id, db))
                continue
            
            # 情况2: 无 insertID 或 insertID 不存在 -> 新增
            # 验证类型
            if node_data.type not in NODE_TYPES:
                errors.append(f"第 {i+1} 行: 无效的节点类型 '{node_data.type}'")
                continue
            
            # 检查名称冲突(无insertID时)
            if node_data.name in name_map:
                # 如果有 insertID，说明是不同 insertID 的新增，允许
                # 如果没有 insertID，报错
                if not node_insert_id:
                    errors.append(f"第 {i+1} 行: 节点名称 '{node_data.name}' 已存在，且无 insertID 无法识别")
                    continue
            
            # 插入新节点
            insert_query = text(f"""
                INSERT INTO {node_table.name} (name, type, description, cluster, insertID, properties, created_at, updated_at)
                VALUES (:name, :type, :description, :cluster, :insertID, :properties, :created_at, :updated_at)
            """)
            
            result = db.execute(insert_query, {
                "name": node_data.name,
                "type": node_data.type,
                "description": node_data.description,
                "cluster": node_data.cluster,
                "insertID": node_insert_id,
                "properties": str(node_data.properties) if node_data.properties else None,
                "created_at": now,
                "updated_at": now
            })
            db.commit()
            
            # 更新内存中的映射(避免同一批次中重复创建)
            if node_insert_id:
                insert_id_map[node_insert_id] = result.lastrowid
            name_map[node_data.name] = result.lastrowid
            
            created_nodes.append(await get_node(system_id, result.lastrowid, db))
        except Exception as e:
            db.rollback()
            errors.append(f"第 {i+1} 行: {str(e)}")
    
    if errors and not created_nodes and not updated_nodes:
        raise HTTPException(status_code=400, detail=f"批量导入失败: {'; '.join(errors)}")
    
    return {
        "created": len(created_nodes),
        "updated": len(updated_nodes),
        "errors": errors if errors else [],
        "nodes": created_nodes + updated_nodes
    }
