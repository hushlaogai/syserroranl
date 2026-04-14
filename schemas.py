"""Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ============= 系统 Schema =============

class SystemBase(BaseModel):
    """系统基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="系统名称")
    description: Optional[str] = Field(None, description="系统描述")
    color: Optional[str] = Field("#6366f1", description="主题颜色")


class SystemCreate(SystemBase):
    """创建系统"""
    pass


class SystemUpdate(BaseModel):
    """更新系统"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None


class SystemResponse(SystemBase):
    """系统响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============= 节点 Schema =============

class NodeBase(BaseModel):
    """节点基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="节点名称")
    type: str = Field(..., description="节点类型")
    description: Optional[str] = Field(None, description="节点描述")
    cluster: Optional[str] = Field(None, max_length=100, description="所属集群(仅用于初始化)")
    insertID: Optional[str] = Field(None, max_length=255, description="导入唯一标识(不显示)")
    properties: Optional[dict] = Field(None, description="扩展属性")


class NodeCreate(NodeBase):
    """创建节点"""
    pass


class NodeUpdate(BaseModel):
    """更新节点"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = None
    description: Optional[str] = None
    # cluster 不可修改（只用于初始化）
    properties: Optional[dict] = None


class NodeResponse(BaseModel):
    """节点响应"""
    id: int
    name: str
    type: str
    description: Optional[str] = None
    cluster: Optional[str] = None
    properties: Optional[dict] = None
    system_id: int
    created_at: datetime
    updated_at: datetime


    class Config:
        from_attributes = True


class NodeBatchCreate(BaseModel):
    """批量创建节点"""
    nodes: List[NodeCreate]


class NodeBatchResponse(BaseModel):
    """批量导入响应"""
    created: int
    updated: int
    errors: List[str]
    nodes: List[dict]


# ============= 边 Schema =============

class EdgeBase(BaseModel):
    """边基础模型"""
    source_id: int = Field(..., description="源节点ID")
    target_id: int = Field(..., description="目标节点ID")
    weight: int = Field(default=5, ge=1, le=10, description="故障权重(1-10)")
    description: Optional[str] = Field(None, description="依赖描述")


class EdgeCreate(EdgeBase):
    """创建边"""
    pass


class EdgeUpdate(BaseModel):
    """更新边"""
    source_id: Optional[int] = None
    target_id: Optional[int] = None
    weight: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = None


class EdgeResponse(EdgeBase):
    """边响应"""
    id: int
    system_id: int
    created_at: datetime
    source_node: Optional[NodeResponse] = None
    target_node: Optional[NodeResponse] = None

    class Config:
        from_attributes = True


class EdgeBatchCreate(BaseModel):
    """批量创建边"""
    edges: List[EdgeCreate]


# ============= 统计 Schema =============

class StatsResponse(BaseModel):
    """统计数据响应"""
    total_nodes: int
    total_edges: int
    nodes_by_type: dict
    edges_by_weight: dict


class SystemStatsResponse(BaseModel):
    """系统统计数据"""
    system: SystemResponse
    total_nodes: int
    total_edges: int
    nodes_by_type: dict
    edges_by_weight: dict


# ============= 导入导出 Schema =============

class ExportData(BaseModel):
    """导出数据结构"""
    system: SystemResponse
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]


class ImportData(BaseModel):
    """导入数据结构"""
    system_name: str
    nodes: List[NodeCreate]
    edges: List[EdgeCreate]
