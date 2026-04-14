"""
哈希处理服务路由
提供 HTTP API 接口供前端调用
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from hash_service import hash_service

router = APIRouter(prefix="/api/hash", tags=["哈希服务"])


class SaltRequest(BaseModel):
    """设置盐值请求"""
    salt: str = Field(..., description="哈希计算使用的盐值", min_length=1)


class SaltResponse(BaseModel):
    """盐值响应"""
    success: bool
    salt: Optional[str] = Field(None, description="当前设置的盐值（部分隐藏）")
    message: str


class HashTaskRequest(BaseModel):
    """单个哈希任务请求"""
    input_data: str = Field(..., description="输入数据字符串", min_length=1)
    pattern: str = Field(..., description="正则表达式模式，用于匹配需要哈希的内容", min_length=1)
    format_template: str = Field(default="{hash}", description="输出格式模板，支持 {hash}, {original}, {salt} 占位符")
    salt: Optional[str] = Field(None, description="可选的独立盐值（覆盖全局盐值）")


class HashTaskResponse(BaseModel):
    """哈希任务响应"""
    task_id: str
    status: str
    message: str


class BatchHashRequest(BaseModel):
    """批量哈希任务请求"""
    tasks: List[HashTaskRequest] = Field(..., min_items=1, max_items=100, description="任务列表，最多100个")


class BatchHashResponse(BaseModel):
    """批量哈希任务响应"""
    task_ids: List[str]
    count: int
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.post("/salt", response_model=SaltResponse)
async def set_salt(request: SaltRequest):
    """
    设置全局盐值
    
    设置后，所有后续的哈希任务都会使用此盐值（除非任务单独指定了盐值）
    """
    try:
        hash_service.set_salt(request.salt)
        # 返回部分隐藏的盐值
        display_salt = request.salt[:4] + "****" + request.salt[-4:] if len(request.salt) > 8 else "****"
        return SaltResponse(
            success=True,
            salt=display_salt,
            message="盐值设置成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置盐值失败: {str(e)}"
        )


@router.get("/salt", response_model=SaltResponse)
async def get_salt():
    """
    获取当前盐值（部分隐藏）
    """
    salt = hash_service.get_salt()
    if salt:
        display_salt = salt[:4] + "****" + salt[-4:] if len(salt) > 8 else "****"
        return SaltResponse(
            success=True,
            salt=display_salt,
            message="盐值已设置"
        )
    else:
        return SaltResponse(
            success=True,
            salt=None,
            message="未设置盐值"
        )


@router.post("/task", response_model=HashTaskResponse)
async def create_hash_task(request: HashTaskRequest):
    """
    创建单个哈希处理任务
    
    示例:
    - input_data: "user:admin,password:123456"
    - pattern: "password:([^,]+)"
    - format_template: "password:HASH_{hash}"
    
    结果: "user:admin,password:HASH_5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    """
    try:
        task_id = hash_service.submit_task(
            input_data=request.input_data,
            pattern=request.pattern,
            format_template=request.format_template,
            salt=request.salt
        )
        return HashTaskResponse(
            task_id=task_id,
            status="pending",
            message="任务已提交，请使用 task_id 查询结果"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.post("/batch", response_model=BatchHashResponse)
async def create_batch_tasks(request: BatchHashRequest):
    """
    批量创建哈希处理任务（最多100个）
    
    适用于需要并行处理大量数据的场景
    """
    try:
        task_dicts = [
            {
                'input_data': t.input_data,
                'pattern': t.pattern,
                'format_template': t.format_template,
                'salt': t.salt
            }
            for t in request.tasks
        ]
        
        task_ids = hash_service.submit_batch(task_dicts)
        return BatchHashResponse(
            task_ids=task_ids,
            count=len(task_ids),
            message=f"成功提交 {len(task_ids)} 个任务"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量创建任务失败: {str(e)}"
        )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态和结果
    
    状态说明:
    - pending: 等待处理
    - processing: 处理中
    - completed: 已完成（可查看 result）
    - failed: 失败（可查看 error）
    """
    status = hash_service.get_task_status(task_id)
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    return TaskStatusResponse(**status)


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks(status: Optional[str] = None):
    """
    获取所有任务列表
    
    可选按状态过滤: pending, processing, completed, failed
    """
    tasks = hash_service.get_all_tasks(status=status)
    return [TaskStatusResponse(**t) for t in tasks]


@router.delete("/tasks/completed")
async def clear_completed_tasks(max_age_seconds: Optional[int] = None):
    """
    清理已完成的任务
    
    可选参数 max_age_seconds: 只清理超过指定秒数的任务
    """
    count = hash_service.clear_completed_tasks(max_age_seconds=max_age_seconds)
    return {
        "success": True,
        "cleared_count": count,
        "message": f"已清理 {count} 个已完成任务"
    }


@router.post("/task/{task_id}/wait")
async def wait_for_task(task_id: str, timeout: Optional[float] = 30.0):
    """
    等待任务完成（同步等待）
    
    timeout: 最大等待秒数，默认30秒
    """
    result = hash_service.wait_for_task(task_id, timeout=timeout)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在"
        )
    
    return TaskStatusResponse(**result)


class HashComputeRequest(BaseModel):
    """直接计算哈希请求"""
    data: str = Field(..., description="要哈希的数据", min_length=1)
    salt: Optional[str] = Field(None, description="可选的盐值")


class HashComputeResponse(BaseModel):
    """直接计算哈希响应"""
    hash: str
    algorithm: str = "SHA-256"


@router.post("/compute", response_model=HashComputeResponse)
async def compute_hash(request: HashComputeRequest):
    """
    直接计算数据的 SHA-256 哈希值
    
    格式: data + salt
    """
    try:
        import hashlib
        content = request.data + (request.salt or "")
        hash_value = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return HashComputeResponse(hash=hash_value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"计算哈希失败: {str(e)}"
        )
