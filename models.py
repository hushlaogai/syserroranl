"""数据模型 - 支持多系统架构"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, event
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class System(Base):
    """系统模型 - 代表一个独立的 IT 系统"""
    __tablename__ = "systems"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")  # 主题颜色
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<System(id={self.id}, name='{self.name}')>"


# 动态表名工厂函数
def get_node_tablename(system_id):
    """获取指定系统的节点表名"""
    return f"nodes_system_{system_id}"


def get_edge_tablename(system_id):
    """获取指定系统的边表名"""
    return f"edges_system_{system_id}"


def create_system_tables(system_id):
    """为指定系统创建独立的 nodes 和 edges 表"""
    from database import engine
    from sqlalchemy import Table, Column, Integer, String, Text, DateTime, JSON, MetaData, ForeignKey

    metadata = MetaData()
    metadata.bind = engine

    # 节点表
    node_table = Table(
        f"nodes_system_{system_id}",
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("name", String(255), nullable=False, index=True),
        Column("type", String(50), nullable=False, index=True),
        Column("description", Text, nullable=True),
        Column("cluster", String(100), nullable=True, index=True),
        Column("insertID", String(255), nullable=True, index=True),
        Column("properties", JSON, nullable=True),
        Column("created_at", DateTime, default=datetime.utcnow),
        Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        extend_existing=True
    )

    # 边表
    edge_table = Table(
        f"edges_system_{system_id}",
        metadata,
        Column("id", Integer, primary_key=True, index=True),
        Column("source_id", Integer, nullable=False, index=True),
        Column("target_id", Integer, nullable=False, index=True),
        Column("weight", Integer, default=1),
        Column("description", Text, nullable=True),
        Column("created_at", DateTime, default=datetime.utcnow),
        extend_existing=True
    )

    # 创建表
    metadata.create_all(engine)
    return node_table, edge_table


def delete_system_tables(system_id):
    """删除指定系统的表"""
    from database import engine
    from sqlalchemy import text

    node_table_name = f"nodes_system_{system_id}"
    edge_table_name = f"edges_system_{system_id}"

    with engine.connect() as conn:
        # 使用原生 SQL 删除表（Table.drop() 在 SQLite 上不可靠）
        conn.execute(text(f"DROP TABLE IF EXISTS {edge_table_name}"))
        conn.execute(text(f"DROP TABLE IF EXISTS {node_table_name}"))
        conn.commit()


def get_system_node_model(system_id):
    """动态创建指定系统的 Node 模型类"""
    from database import Base

    node_table_name = get_node_tablename(system_id)

    # 检查是否已存在
    if hasattr(Base.metadata, 'tables') and node_table_name in Base.metadata.tables:
        return None

    # 动态创建模型类
    NodeClass = type(
        f'NodeSystem{system_id}',
        (Base,),
        {
            '__tablename__': node_table_name,
            'id': Column(Integer, primary_key=True, index=True),
            'name': Column(String(255), nullable=False, index=True),
            'type': Column(String(50), nullable=False, index=True),
            'description': Column(Text, nullable=True),
            'cluster': Column(String(100), nullable=True, index=True),
            'insertID': Column(String(255), nullable=True, index=True),
            'properties': Column(JSON, nullable=True),
            'created_at': Column(DateTime, default=datetime.utcnow),
            'updated_at': Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
        }
    )
    return NodeClass


def get_system_edge_model(system_id):
    """动态创建指定系统的 Edge 模型类"""
    from database import Base

    edge_table_name = get_edge_tablename(system_id)

    # 检查是否已存在
    if hasattr(Base.metadata, 'tables') and edge_table_name in Base.metadata.tables:
        return None

    # 动态创建模型类
    EdgeClass = type(
        f'EdgeSystem{system_id}',
        (Base,),
        {
            '__tablename__': edge_table_name,
            'id': Column(Integer, primary_key=True, index=True),
            'source_id': Column(Integer, nullable=False, index=True),
            'target_id': Column(Integer, nullable=False, index=True),
            'weight': Column(Integer, default=1),
            'description': Column(Text, nullable=True),
            'created_at': Column(DateTime, default=datetime.utcnow),
        }
    )
    return EdgeClass
