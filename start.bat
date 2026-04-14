@echo off
chcp 65001 >nul
echo ========================================
echo syserroranl 系统故障分析应用
echo ========================================
echo.
echo 正在启动服务器...
cd /d "%~dp0"
start "" python -m uvicorn app:app --host 0.0.0.0 --port 8000
echo 服务器已启动: http://localhost:8000
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:8000
