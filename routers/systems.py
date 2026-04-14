"""系统路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from database import get_db
from models import System, create_system_tables, delete_system_tables
from schemas import SystemCreate, SystemUpdate, SystemResponse

router = APIRouter(prefix="/api/systems", tags=["系统管理"])


@router.get("", response_model=List[SystemResponse])
async def get_all_systems(db: Session = Depends(get_db)):
    """获取所有系统"""
    systems = db.query(System).order_by(System.created_at.desc()).all()
    return systems


@router.get("/{system_id}", response_model=SystemResponse)
async def get_system(system_id: int, db: Session = Depends(get_db)):
    """获取单个系统"""
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"系统 {system_id} 不存在"
        )
    return system


@router.post("", response_model=SystemResponse, status_code=status.HTTP_201_CREATED)
async def create_system(system_data: SystemCreate, db: Session = Depends(get_db)):
    """创建新系统（同时创建对应的节点和边表，并自动创建一个类型为"系统"的节点）"""
    # 检查重名
    existing = db.query(System).filter(System.name == system_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"系统名称 '{system_data.name}' 已存在"
        )

    # 创建系统记录
    system = System(**system_data.model_dump())
    db.add(system)
    db.commit()
    db.refresh(system)

    # 为新系统创建独立的节点和边表
    try:
        create_system_tables(system.id)
    except Exception as e:
        # 回滚系统创建
        db.delete(system)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建系统表失败: {str(e)}"
        )

    # 自动创建一个类型为"系统"的节点
    try:
        from datetime import datetime
        node_table_name = f"nodes_system_{system.id}"
        now = datetime.utcnow()
        insert_query = text(f"""
            INSERT INTO {node_table_name} (name, type, description, cluster, insertID, properties, created_at, updated_at)
            VALUES (:name, :type, :description, :cluster, :insertID, :properties, :created_at, :updated_at)
        """)
        db.execute(insert_query, {
            "name": system.name,
            "type": "系统",
            "description": system.description or f"系统: {system.name}",
            "cluster": None,
            "insertID": f"SYS_{system.id}",
            "properties": None,
            "created_at": now,
            "updated_at": now
        })
        db.commit()
    except Exception as e:
        # 节点创建失败不影响系统创建，记录错误即可
        print(f"自动创建系统节点失败: {e}")

    return system


@router.put("/{system_id}", response_model=SystemResponse)
async def update_system(system_id: int, system_data: SystemUpdate, db: Session = Depends(get_db)):
    """更新系统"""
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"系统 {system_id} 不存在"
        )

    update_data = system_data.model_dump(exclude_unset=True)

    # 检查重名
    if "name" in update_data and update_data["name"]:
        existing = db.query(System).filter(
            System.name == update_data["name"],
            System.id != system_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"系统名称 '{update_data['name']}' 已存在"
            )

    for key, value in update_data.items():
        setattr(system, key, value)

    db.commit()
    db.refresh(system)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system(system_id: int, db: Session = Depends(get_db)):
    """删除系统（同时删除对应的节点和边表）"""
    system = db.query(System).filter(System.id == system_id).first()
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"系统 {system_id} 不存在"
        )

    # 删除系统表
    try:
        delete_system_tables(system_id)
    except Exception:
        pass  # 忽略表删除错误

    # 删除系统记录
    db.delete(system)
    db.commit()
    return None
