from fastapi import FastAPI

app = FastAPI(title="ChicFinder")

@app.get("/")
async def root():
    return {"service": "ChicFinder API", "version": "1.0"}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "ChicFinder API"}
