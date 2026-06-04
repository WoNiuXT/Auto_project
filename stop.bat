@echo off
chcp 65001 >nul
echo 正在停止所有服务...

:: 停止前端和后端
taskkill /F /IM node.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq npx*" 2>nul

:: 停止 ComfyUI (Python 进程中 port 8188 的)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8188 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

:: 停止 FastAPI (Python 进程中 port 8000 的)  
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

:: 停止 Docker 容器
docker compose down

echo 所有服务已停止!
pause