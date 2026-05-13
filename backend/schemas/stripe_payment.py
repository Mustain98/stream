from sqlmodel import SQLModel


class ReconcileCheckoutRequest(SQLModel):
    checkout_session_id: str