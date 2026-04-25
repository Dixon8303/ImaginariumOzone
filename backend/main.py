from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import database
from routers import episodes, pipeline, assets, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield

app = FastAPI(
    title="Black Genius Files — Production OS",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(episodes.router)
app.include_router(pipeline.router)
app.include_router(assets.router)
app.include_router(analytics.router)

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "BGF Production OS v1.0"}
