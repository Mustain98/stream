from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from core.security import get_current_user
from db.session import get_session
from controllers.stream_ticket_controller import create_sfu_ticket_controller

router = APIRouter(prefix="/sfu", tags=["sfu"])


@router.post("/ticket/{stream_id}")
def get_sfu_ticket(
    stream_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    response, error = create_sfu_ticket_controller(
        session=session,
        stream_id=stream_id,
        user=user,
    )

    if error == "stream_not_found":
        raise HTTPException(status_code=404, detail="Stream not found")

    if error == "blocked":
        raise HTTPException(status_code=403, detail="You are blocked from this stream")

    if error == "publisher_stream_not_live":
        raise HTTPException(
            status_code=400,
            detail="Start the stream before requesting an SFU ticket",
        )

    if error == "stream_not_live":
        raise HTTPException(status_code=400, detail="Stream is not live")

    return response