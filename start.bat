@echo off
chcp 65001 >nul
echo ========================================
echo   Auto_pipeline 一键启动
echo ========================================
echo.

:: 1. Docker (PostgreSQL + DailyHotApi)
echo [1/4] 启动 Docker 容器...
docker compose up -d
timeout /t 5 >nul

:: 2. ComfyUI (图片生成引擎)
echo [2/4] 启动 ComfyUI (GPU)...
start "" /min cmd /c "C:\Python310\python.exe C:\Users\王鑫涛\ComfyUI\main.py --listen 127.0.0.1 --port 8188 --lowvram"
timeout /t 15 >nul

:: 3. FastAPI 后端
echo [3/4] 启动 FastAPI 后端 (端口 8000)...
start "" /min cmd /c "cd /d D:\Agent_Project\Auto_project && C:\Python310\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 >nul

:: 4. Vue 前端
echo [4/4] 启动 Vue 前端 (端口 5173)...
start "" /min cmd /c "cd /d D:\Agent_Project\Auto_project\frontend && npx vite --host"
timeout /t 3 >nul

echo.
echo ========================================
echo   所有服务已启动!
echo ========================================
echo.
echo   ComfyUI:   http://127.0.0.1:8188  (图片生成引擎)
echo   FastAPI:   http://127.0.0.1:8000  (后端 API)
echo   Vue 前端:  http://127.0.0.1:5173  (管理界面)
echo   DailyHot:  http://127.0.0.1:6688  (热点 API)
echo   PostgreSQL: localhost:5434         (数据库)
echo.
echo   关闭: 运行 stop.bat
echo ========================================
pause