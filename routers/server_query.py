"""
服务器查询路由 - 通过哈希值查询服务器信息
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from database import get_db
from models import System

router = APIRouter(prefix="/api/server-query", tags=["服务器查询"])


class ServerQueryRequest(BaseModel):
    """服务器查询请求"""
    hash_value: str = Field(..., description="IP 的哈希值", min_length=1)
    system_id: Optional[int] = Field(None, description="指定系统ID，不指定则查询所有系统")


class ComponentInfo(BaseModel):
    """组件信息"""
    id: int
    name: str
    type: str
    description: Optional[str] = None


class ServerQueryResponse(BaseModel):
    """服务器查询响应"""
    found: bool
    system_id: Optional[int] = None
    system_name: Optional[str] = None
    server: Optional[Dict[str, Any]] = None
    cluster: Optional[Dict[str, Any]] = None
    components: List[ComponentInfo] = []
    message: str


def get_node_table_name(system_id: int) -> str:
    return f"nodes_system_{system_id}"


def get_edge_table_name(system_id: int) -> str:
    return f"edges_system_{system_id}"


@router.post("/by-hash", response_model=ServerQueryResponse)
async def query_server_by_hash(request: ServerQueryRequest, db: Session = Depends(get_db)):
    """
    通过哈希值查询服务器信息
    
    查询逻辑：
    1. 在所有系统的服务器节点中查找 name 匹配哈希值的服务器
    2. 找到服务器后，通过边关系查找：
       - 所属集群（source: 集群 -> target: 服务器）
       - 所属组件（source: 服务器 -> target: 组件）
    """
    from sqlalchemy import inspect
    from database import engine
    
    inspector = inspect(engine)
    
    # 确定要查询的系统列表
    if request.system_id:
        systems = db.query(System).filter(System.id == request.system_id).all()
    else:
        systems = db.query(System).all()
    
    for system in systems:
        node_table_name = get_node_table_name(system.id)
        edge_table_name = get_edge_table_name(system.id)
        
        # 检查表是否存在
        if not inspector.has_table(node_table_name):
            continue
        
        # 1. 查找匹配哈希值的服务器
        # 哈希值存储在 description 字段，格式为 "IP: <hash_value>"
        server_query = text(f"""
            SELECT id, name, type, description, properties, cluster 
            FROM {node_table_name} 
            WHERE type = '服务器' AND description LIKE :hash_pattern
            LIMIT 1
        """)
        server_result = db.execute(server_query, {"hash_pattern": f"%: {request.hash_value}"})
        server_row = server_result.fetchone()
        
        if not server_row:
            continue
        
        # 找到服务器，构造返回数据
        server_data = {
            "id": server_row[0],
            "name": server_row[1],
            "type": server_row[2],
            "description": server_row[3],
            "properties": server_row[4],
            "cluster_insert_id": server_row[5]
        }
        
        # 2. 查找所属集群
        cluster_data = None
        if server_row[5]:  # 如果有 cluster 字段（存储集群的 insertID）
            cluster_query = text(f"""
                SELECT id, name, type, description 
                FROM {node_table_name} 
                WHERE type = '集群' AND insertID = :cluster_id
                LIMIT 1
            """)
            cluster_result = db.execute(cluster_query, {"cluster_id": server_row[5]})
            cluster_row = cluster_result.fetchone()
            if cluster_row:
                cluster_data = {
                    "id": cluster_row[0],
                    "name": cluster_row[1],
                    "type": cluster_row[2],
                    "description": cluster_row[3]
                }
        
        # 3. 查找所属组件（通过边关系）
        components = []
        if inspector.has_table(edge_table_name):
            # 查找从该服务器出发的边，目标是组件
            components_query = text(f"""
                SELECT n.id, n.name, n.type, n.description
                FROM {edge_table_name} e
                JOIN {node_table_name} n ON e.target_id = n.id
                WHERE e.source_id = :server_id AND n.type = '组件'
            """)
            comp_result = db.execute(components_query, {"server_id": server_row[0]})
            for comp_row in comp_result.fetchall():
                components.append(ComponentInfo(
                    id=comp_row[0],
                    name=comp_row[1],
                    type=comp_row[2],
                    description=comp_row[3]
                ))
        
        return ServerQueryResponse(
            found=True,
            system_id=system.id,
            system_name=system.name,
            server=server_data,
            cluster=cluster_data,
            components=components,
            message="查询成功"
        )
    
    # 未找到匹配的服务器
    return ServerQueryResponse(
        found=False,
        message="未找到匹配的服务器"
    )


@router.get("/systems")
async def get_systems_for_query(db: Session = Depends(get_db)):
    """获取可用于查询的系统列表"""
    systems = db.query(System).all()
    return [
        {"id": s.id, "name": s.name}
        for s in systems
    ]
