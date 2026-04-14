"""syserroranl - 系统故障分析应用 (多系统版)"""
from fastapi import FastAPI, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import Optional
import json

from database import init_db, get_db, SessionLocal
from models import System
from schemas import (
    StatsResponse, SystemStatsResponse, ExportData, ImportData, 
    NodeCreate, EdgeCreate, SystemCreate
)
from routers import systems, nodes, edges, hash, server_query

# 创建 FastAPI 应用
app = FastAPI(
    title="syserroranl - 系统故障分析",
    description="IT系统故障分析基础数据库 - 支持多系统管理",
    version="2.0.0"
)

# 注册路由
app.include_router(systems.router)
app.include_router(nodes.router)
app.include_router(edges.router)
app.include_router(hash.router)
app.include_router(server_query.router)


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


# ==================== 统计 API ====================

def get_node_table_name(system_id: int) -> str:
    return f"nodes_system_{system_id}"


def get_edge_table_name(system_id: int) -> str:
    return f"edges_system_{system_id}"


@app.get("/api/systems/{system_id}/stats", response_model=SystemStatsResponse)
async def get_system_stats(system_id: int, db: Session = Depends(get_db)):
    """获取指定系统的统计数据"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return JSONResponse(
            status_code=404,
            content={"detail": f"系统 {system_id} 不存在"}
        )
    
    inspector = inspect(engine)
    node_table_name = get_node_table_name(system_id)
    edge_table_name = get_edge_table_name(system_id)
    
    total_nodes = 0
    total_edges = 0
    nodes_by_type = {}
    edges_by_weight = {}
    
    if inspector.has_table(node_table_name):
        # 统计节点数
        count_query = text(f"SELECT COUNT(*) FROM {node_table_name}")
        result = db.execute(count_query)
        total_nodes = result.scalar() or 0
        
        # 按类型统计
        type_query = text(f"SELECT type, COUNT(*) FROM {node_table_name} GROUP BY type")
        type_result = db.execute(type_query)
        for row in type_result.fetchall():
            nodes_by_type[row[0]] = row[1]
    
    if inspector.has_table(edge_table_name):
        # 统计边数
        count_query = text(f"SELECT COUNT(*) FROM {edge_table_name}")
        result = db.execute(count_query)
        total_edges = result.scalar() or 0
        
        # 按权重统计
        weight_query = text(f"SELECT weight, COUNT(*) FROM {edge_table_name} GROUP BY weight")
        weight_result = db.execute(weight_query)
        for row in weight_result.fetchall():
            edges_by_weight[row[0]] = row[1]
    
    return SystemStatsResponse(
        system=system,
        total_nodes=total_nodes,
        total_edges=total_edges,
        nodes_by_type=nodes_by_type,
        edges_by_weight=edges_by_weight
    )


@app.get("/api/systems/{system_id}/graph", response_model=dict)
async def get_graph_data(system_id: int, db: Session = Depends(get_db)):
    """获取图数据（用于可视化）"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return JSONResponse(status_code=404, content={"detail": f"系统 {system_id} 不存在"})
    
    inspector = inspect(engine)
    node_table_name = get_node_table_name(system_id)
    edge_table_name = get_edge_table_name(system_id)
    
    nodes_list = []
    edges_list = []
    
    if inspector.has_table(node_table_name):
        nodes_query = text(f"SELECT * FROM {node_table_name}")
        nodes_result = db.execute(nodes_query)
        for row in nodes_result.fetchall():
            node = dict(zip(nodes_result.keys(), row))
            node['system_id'] = system_id
            if node.get('created_at'):
                node['created_at'] = node['created_at'].isoformat() if hasattr(node['created_at'], 'isoformat') else str(node['created_at'])
            if node.get('updated_at'):
                node['updated_at'] = node['updated_at'].isoformat() if hasattr(node['updated_at'], 'isoformat') else str(node['updated_at'])
            nodes_list.append(node)
    
    if inspector.has_table(edge_table_name):
        edges_query = text(f"SELECT * FROM {edge_table_name}")
        edges_result = db.execute(edges_query)
        for row in edges_result.fetchall():
            edge = dict(zip(edges_result.keys(), row))
            edge['system_id'] = system_id
            if edge.get('created_at'):
                edge['created_at'] = edge['created_at'].isoformat() if hasattr(edge['created_at'], 'isoformat') else str(edge['created_at'])
            edges_list.append(edge)
    
    return {"nodes": nodes_list, "edges": edges_list}


@app.get("/api/systems/{system_id}/export")
async def export_system_data(system_id: int, db: Session = Depends(get_db)):
    """导出指定系统的数据为JSON"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return JSONResponse(status_code=404, content={"detail": f"系统 {system_id} 不存在"})
    
    inspector = inspect(engine)
    node_table_name = get_node_table_name(system_id)
    edge_table_name = get_edge_table_name(system_id)
    
    nodes_data = []
    edges_data = []
    
    if inspector.has_table(node_table_name):
        nodes_query = text(f"SELECT * FROM {node_table_name}")
        nodes_result = db.execute(nodes_query)
        for row in nodes_result.fetchall():
            node = dict(zip(nodes_result.keys(), row))
            node['created_at'] = node['created_at'].isoformat() if hasattr(node['created_at'], 'isoformat') and node['created_at'] else None
            node['updated_at'] = node['updated_at'].isoformat() if hasattr(node['updated_at'], 'isoformat') and node['updated_at'] else None
            nodes_data.append(node)
    
    if inspector.has_table(edge_table_name):
        edges_query = text(f"SELECT * FROM {edge_table_name}")
        edges_result = db.execute(edges_query)
        for row in edges_result.fetchall():
            edge = dict(zip(edges_result.keys(), row))
            edge['created_at'] = edge['created_at'].isoformat() if hasattr(edge['created_at'], 'isoformat') and edge['created_at'] else None
            edges_data.append(edge)
    
    return JSONResponse(content={
        "system": {
            "id": system.id,
            "name": system.name,
            "description": system.description,
            "color": system.color
        },
        "nodes": nodes_data,
        "edges": edges_data
    })


@app.post("/api/import")
async def import_data(data: ImportData, db: Session = Depends(get_db)):
    """导入系统数据"""
    # 检查系统是否存在
    existing = db.query(System).filter(System.name == data.system_name).first()
    if existing:
        return JSONResponse(
            status_code=400,
            content={"detail": f"系统 '{data.system_name}' 已存在，请使用其他名称"}
        )
    
    # 创建系统
    system = System(name=data.system_name)
    db.add(system)
    db.commit()
    db.refresh(system)
    
    # 创建表
    from models import create_system_tables
    create_system_tables(system.id)
    
    # 创建节点
    node_name_to_id = {}
    for node_data in data.nodes:
        from routers.nodes import get_node_table
        node_table = get_node_table(system.id)
        
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
        node_name_to_id[node_data.name] = result.lastrowid
    
    # 创建边
    created_edges = 0
    for edge_data in data.edges:
        from routers.nodes import get_edge_table
        edge_table = get_edge_table(system.id)
        if not edge_table:
            continue
        
        # 通过名称查找 ID
        source_id = node_name_to_id.get(edge_data.source_id if isinstance(edge_data.source_id, str) else str(edge_data.source_id))
        target_id = node_name_to_id.get(edge_data.target_id if isinstance(edge_data.target_id, str) else str(edge_data.target_id))
        
        if source_id and target_id:
            from datetime import datetime
            now = datetime.utcnow()
            
            insert_query = text(f"""
                INSERT INTO {edge_table.name} (source_id, target_id, weight, description, created_at)
                VALUES (:source_id, :target_id, :weight, :description, :created_at)
            """)
            
            db.execute(insert_query, {
                "source_id": source_id,
                "target_id": target_id,
                "weight": edge_data.weight,
                "description": edge_data.description,
                "created_at": now
            })
            db.commit()
            created_edges += 1
    
    return JSONResponse(content={
        "success": True,
        "system_id": system.id,
        "system_name": system.name,
        "created_nodes": len(data.nodes),
        "created_edges": created_edges
    })


@app.get("/api/search")
async def search_nodes(system_id: int, q: str = "", db: Session = Depends(get_db)):
    """搜索节点"""
    # 验证系统存在
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        return JSONResponse(status_code=404, content={"detail": f"系统 {system_id} 不存在"})
    
    if not q:
        return []
    
    from routers.nodes import get_node_table
    node_table = get_node_table(system_id)
    
    query = text(f"""
        SELECT id, name, type FROM {node_table.name} 
        WHERE name LIKE :q OR description LIKE :q
        LIMIT 20
    """)
    result = db.execute(query, {"q": f"%{q}%"})
    
    return [
        {"id": row[0], "name": row[1], "type": row[2]}
        for row in result.fetchall()
    ]


# 导入 engine 用于 inspect
from database import engine

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
