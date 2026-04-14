"""数据库配置"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import os

# 数据库路径：优先使用环境变量（打包后写入可写目录），否则用项目目录
_default_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "syserroranl.db")
DB_PATH = os.environ.get('SYSERRORANL_DB_PATH', _default_db_path)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 创建引擎
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明性基类
Base = declarative_base()

# 全局元数据（用于创建表）
metadata = Base.metadata


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    from models import System
    # 创建所有表（System 表等静态表）
    Base.metadata.create_all(bind=engine)
