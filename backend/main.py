# backend/main.py

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from db.session import engine

from routes.auth import router as auth_router
from routes.stream import router as stream_router
from routes.websocket_ticket import router as sfu_ticket_router


app = FastAPI(title="Main Stream Backend")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_origin,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(engine)

app.include_router(auth_router)
app.include_router(stream_router)
app.include_router(sfu_ticket_router)


@app.get("/")
def root():
    return {
        "status": "main backend ready",
        "responsibility": "auth, database, stream metadata, SFU ticket generation",
    }