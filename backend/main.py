# backend/main.py

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from db.session import engine

from routes.auth import router as auth_router
from routes.stream import router as stream_router
from routes.stream_ticket import router as sfu_ticket_router
from routes.stream_server import router as sfu_internal_router
from routes.stream_control import router as stream_control_router
from routes.transaction import router as transaction_router
from services.stream_cleanup import stream_cleanup_loop
from routes.stripe_payment import router as stripe_payment_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)

    cleanup_task = asyncio.create_task(stream_cleanup_loop())

    try:
        yield
    finally:
        cleanup_task.cancel()

        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Main Stream Backend",
    lifespan=lifespan,
)

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

app.include_router(auth_router)
app.include_router(stream_router)
app.include_router(sfu_ticket_router)
app.include_router(sfu_internal_router)
app.include_router(stream_control_router)
app.include_router(transaction_router)
app.include_router(stripe_payment_router)


@app.get("/")
def root():
    return {
        "status": "main backend ready",
        "responsibility": "auth, database, stream metadata, SFU ticket generation",
    }