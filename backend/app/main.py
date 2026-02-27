from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import ingest, retrieve

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/ingest")

@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(retrieve.router, prefix="/query")