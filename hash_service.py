"""
后台哈希处理服务模块
功能：将输入数据通过 SHA-256 算法计算后，按输入格式替换输出
特点：
- 离线运行，无互联网依赖（使用标准库 hashlib）
- 支持并行处理多个请求
- 支持动态设置盐值
- 伴随系统启动和停止
"""
import hashlib
import re
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HashTask:
    """哈希任务数据结构"""
    task_id: str
    input_data: str
    pattern: str  # 正则表达式模式，用于匹配需要替换的内容
    format_template: str  # 输出格式模板，如 "HASH:{hash}"
    salt: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class HashService:
    """
    哈希处理服务类
    - 单例模式，确保全局唯一实例
    - 线程安全的盐值管理
    - 线程池并行处理任务
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_workers: int = 4):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._salt: Optional[str] = None
        self._salt_lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="hash_worker")
        self._tasks: Dict[str, HashTask] = {}
        self._tasks_lock = threading.RLock()
        
        logger.info(f"HashService initialized with {max_workers} workers")
    
    def set_salt(self, salt: str) -> None:
        """设置全局盐值（线程安全）"""
        with self._salt_lock:
            self._salt = salt
            logger.info(f"Salt updated: {salt[:10]}..." if len(salt) > 10 else f"Salt updated: {salt}")
    
    def get_salt(self) -> Optional[str]:
        """获取当前盐值（线程安全）"""
        with self._salt_lock:
            return self._salt
    
    def _compute_sha256(self, data: str, salt: Optional[str] = None) -> str:
        """
        计算 SHA-256 哈希值
        - 如果设置了盐值，会将数据与盐拼接后计算
        - 格式: data + salt 或 data（无盐时）
        """
        content = data + (salt or "")
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _process_task(self, task: HashTask) -> HashTask:
        """处理单个哈希任务"""
        try:
            task.status = "processing"
            
            # 获取当前盐值（任务创建时的盐值或当前全局盐值）
            salt = task.salt or self.get_salt()
            
            # 使用正则表达式查找所有匹配项
            pattern = re.compile(task.pattern)
            matches = pattern.findall(task.input_data)
            
            if not matches:
                # 无匹配项，返回原数据
                task.result = task.input_data
                task.status = "completed"
                task.completed_at = datetime.now()
                return task
            
            # 处理结果
            result = task.input_data
            for match in matches:
                # 计算哈希值
                hash_value = self._compute_sha256(match, salt)
                
                # 按格式模板生成替换内容
                replacement = task.format_template.format(
                    hash=hash_value,
                    original=match,
                    salt=salt or ""
                )
                
                # 替换第一个匹配项（如需替换所有，可改为 re.sub）
                result = result.replace(match, replacement, 1)
            
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now()
            logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task {task.task_id} failed: {e}")
        
        return task
    
    def submit_task(self, input_data: str, pattern: str, format_template: str, 
                    salt: Optional[str] = None, task_id: Optional[str] = None) -> str:
        """
        提交哈希处理任务
        
        Args:
            input_data: 输入数据字符串
            pattern: 正则表达式模式，用于匹配需要哈希的内容
            format_template: 输出格式模板，支持 {hash}, {original}, {salt} 占位符
            salt: 可选的独立盐值（如未提供则使用全局盐值）
            task_id: 可选的任务ID（自动生成UUID）
        
        Returns:
            task_id: 任务ID，用于查询结果
        """
        import uuid
        
        task_id = task_id or str(uuid.uuid4())
        
        task = HashTask(
            task_id=task_id,
            input_data=input_data,
            pattern=pattern,
            format_template=format_template,
            salt=salt
        )
        
        with self._tasks_lock:
            self._tasks[task_id] = task
        
        # 提交到线程池异步执行
        future = self._executor.submit(self._process_task, task)
        
        logger.info(f"Task {task_id} submitted")
        return task_id
    
    def submit_batch(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        批量提交任务
        
        Args:
            tasks: 任务列表，每个任务是包含 input_data, pattern, format_template 的字典
        
        Returns:
            task_ids: 任务ID列表
        """
        task_ids = []
        for task_data in tasks:
            task_id = self.submit_task(
                input_data=task_data['input_data'],
                pattern=task_data['pattern'],
                format_template=task_data.get('format_template', '{hash}'),
                salt=task_data.get('salt')
            )
            task_ids.append(task_id)
        
        return task_ids
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._tasks_lock:
            task = self._tasks.get(task_id)
        
        if not task:
            return None
        
        return {
            'task_id': task.task_id,
            'status': task.status,
            'result': task.result,
            'error': task.error,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict]:
        """获取所有任务（可选按状态过滤）"""
        with self._tasks_lock:
            tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return [
            {
                'task_id': t.task_id,
                'status': t.status,
                'result': t.result,
                'error': t.error,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None
            }
            for t in tasks
        ]
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Dict]:
        """等待任务完成并返回结果"""
        import time
        
        start_time = time.time()
        while True:
            status = self.get_task_status(task_id)
            if not status:
                return None
            
            if status['status'] in ('completed', 'failed'):
                return status
            
            if timeout and (time.time() - start_time) > timeout:
                return status
            
            time.sleep(0.1)
    
    def clear_completed_tasks(self, max_age_seconds: Optional[int] = None) -> int:
        """清理已完成的任务"""
        with self._tasks_lock:
            to_remove = []
            for task_id, task in self._tasks.items():
                if task.status in ('completed', 'failed'):
                    if max_age_seconds and task.completed_at:
                        age = (datetime.now() - task.completed_at).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(task_id)
                    else:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self._tasks[task_id]
        
        logger.info(f"Cleared {len(to_remove)} completed tasks")
        return len(to_remove)
    
    def shutdown(self):
        """关闭服务，释放资源"""
        logger.info("Shutting down HashService...")
        self._executor.shutdown(wait=True)
        self._tasks.clear()
        logger.info("HashService shutdown complete")


# 全局服务实例
hash_service = HashService(max_workers=4)
