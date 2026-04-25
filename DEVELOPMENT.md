# Development Setup Guide

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- All dependencies installed (see Installation)

### Installation

1. **Python dependencies** (one-time):
```bash
pip install -r requirements.txt
```

2. **Frontend dependencies** (one-time):
```bash
cd FrontEnd
npm install
cd ..
```

## Running Development Servers

### Option 1: Using Startup Scripts (Recommended)

**Windows:**
```bash
dev-server.bat
```

**macOS/Linux:**
```bash
chmod +x dev-server.sh
./dev-server.sh
```

This will start both servers and open them in separate terminal windows.

### Option 2: Manual Startup

**Terminal 1 - Backend (FastAPI on port 8000):**
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend (Next.js on port 3000):**
```bash
cd FrontEnd
npm run dev
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | ChicFinder application |
| Backend API | http://localhost:8000 | REST API endpoints |
| API Docs | http://localhost:8000/docs | Swagger UI documentation |
| API ReDoc | http://localhost:8000/redoc | ReDoc documentation |

## Configuration

### Port Numbers

**Default Development Ports:**
- Frontend: **3000** (configured in `next.config.js`)
- Backend: **8000** (configured in `api.main:app`)

To change ports, modify:
- Frontend port: `FrontEnd/next.config.js` → `server.port`
- Backend port: Use `--port` flag when starting uvicorn

### Environment Variables

Create `FrontEnd/.env.local` with:

```env
# Backend API (required for frontend)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Firebase Configuration (required for authentication)
NEXT_PUBLIC_FIREBASE_API_KEY=your_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_domain
# ... other Firebase config
```

See `FrontEnd/.env.example` for all required variables.

## Troubleshooting

### Port Already in Use
If you see "Port 3000/8000 is already in use":

**Windows:**
```bash
netstat -ano | find ":3000"
taskkill /PID <PID> /F
```

**macOS/Linux:**
```bash
lsof -ti:3000 | xargs kill -9
```

### Backend Connection Errors
If frontend shows "Failed to connect to backend":
1. Verify backend is running on port 8000
2. Check `NEXT_PUBLIC_API_URL` in `.env.local`
3. Ensure CORS is enabled (it should be by default)

### Module Not Found Errors
```bash
# Clear cache and reinstall
cd FrontEnd
rm -rf node_modules .next
npm install
npm run dev
```

## Development Workflow

1. Make changes to code
2. Both servers auto-reload (Uvicorn + Turbopack)
3. Check browser at http://localhost:3000
4. Check API docs at http://localhost:8000/docs

## Building for Production

```bash
# Build frontend
cd FrontEnd
npm run build
npm run start  # Runs on port 3000

# Backend (for production deployment)
# Use gunicorn or similar instead of uvicorn
```

