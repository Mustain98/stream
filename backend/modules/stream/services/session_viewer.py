from datetime import datetime

from sqlmodel import Session, select

from models import ViewerSession


def create_viewer_session(user_id: str, stream_id: str) -> ViewerSession:
    return ViewerSession(
        stream_id=stream_id,
        user_id=user_id,
        is_active=True,
    )


def get_active_viewer(
    session: Session,
    user_id: str,
    stream_id: str,
):
    return session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
            ViewerSession.user_id == user_id,
            ViewerSession.is_active == True,
        )
    ).first()


def get_active_viewers(
    session: Session,
    stream_id: str,
) -> list[ViewerSession]:
    return session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
            ViewerSession.is_active == True,
        )
    ).all()


def get_viewer_sessions_for_stream(
    session: Session,
    stream_id: str,
) -> list[ViewerSession]:
    return session.exec(
        select(ViewerSession).where(
            ViewerSession.stream_id == stream_id,
        )
    ).all()


def make_viewer_inactive(
    session: Session,
    viewer: ViewerSession,
) -> ViewerSession:
    viewer.is_active = False
    viewer.left_at = datetime.utcnow()

    session.add(viewer)

    return viewer


def make_active_viewers_inactive(
    session: Session,
    stream_id: str,
) -> int:
    active_viewers = get_active_viewers(session, stream_id)

    for viewer in active_viewers:
        make_viewer_inactive(session, viewer)

    return len(active_viewers)


def get_unique_viewer_count(
    session: Session,
    stream_id: str,
) -> int:
    viewer_sessions = get_viewer_sessions_for_stream(session, stream_id)

    unique_user_ids = {
        viewer.user_id
        for viewer in viewer_sessions
        if viewer.user_id is not None
    }

    return len(unique_user_ids)