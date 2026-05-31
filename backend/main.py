# backend/main.py

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from db.session import engine

from modules.auth.router import router as auth_router
from modules.stream.routers.stream_router import router as stream_router
from modules.stream.routers.stream_ticket_router import router as sfu_ticket_router
from modules.stream.routers.stream_server_router import router as sfu_internal_router
from modules.stream.routers.stream_control_router import router as stream_control_router
from modules.payment.routers.transaction_router import router as transaction_router
from modules.payment.routers.stripe_payment_router import router as stripe_payment_router
from modules.payment.routers.stripe_connect_router import router as stripe_connect_router
from modules.stream.routers.internal_preview_router import router as preview_router
from modules.stream.services.stream_cleanup import stream_cleanup_loop


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

frontend_origin = os.getenv("FRONTEND_ORIGIN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_origin,
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
app.include_router(stripe_connect_router)
app.include_router(preview_router)


@app.get("/")
def root():
    return {
        "status": "main backend ready",
        "responsibility": "auth, database, stream metadata, SFU ticket generation",
    }