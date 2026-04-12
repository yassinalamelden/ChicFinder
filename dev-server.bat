@echo off
REM ChicFinder Development Server Startup Script (Windows)
REM Starts both the FastAPI backend and Next.js frontend on their configured ports

echo ================================================
echo ChicFinder Development Servers
echo ================================================
echo.
echo Backend (FastAPI):  http://localhost:8000
echo Frontend (Next.js): http://localhost:3000
echo API Docs:           http://localhost:8000/docs
echo.
echo To stop the servers, press Ctrl+C
echo ================================================
echo.

REM Kill any existing processes on our ports
echo Checking for existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000"') do taskkill /PID %%a /F 2>/dev/null
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000"') do taskkill /PID %%a /F 2>/dev/null
timeout /t 1 /nobreak

REM Start FastAPI backend
echo Starting FastAPI backend (port 8000)...
start "ChicFinder Backend" cmd /k python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

REM Wait for backend to start
timeout /t 2 /nobreak

REM Start Next.js frontend
echo Starting Next.js frontend (port 3000)...
cd website_fullstack
start "ChicFinder Frontend" cmd /k npm run dev

echo.
echo ✅ Both servers are starting in separate windows...
pause
