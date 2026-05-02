import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel
from db.session import engine

from routes.auth import router as auth_router
from routes.stream import router as stream_router
from routes.websocket_ticket import router as ticket_router
from routes.ws_stream import router as ws_stream_router

app = FastAPI()

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin,"http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SQLModel.metadata.create_all(engine)

app.include_router(auth_router)
app.include_router(stream_router)
app.include_router(ticket_router)
app.include_router(ws_stream_router)


@app.get("/")
def root():
    return {"status": "auth system ready"}
