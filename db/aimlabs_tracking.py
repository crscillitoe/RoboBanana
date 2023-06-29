from sqlalchemy import insert
from db.models import AimlabsTracking
from sqlalchemy.orm import sessionmaker


def register_user(
    user_id: int,
    aimlabs_id: str,
    timezone: str,
    session: sessionmaker,
):
    """Register new user for Aimlabs Tracking

    Args:
        user_id (int): Discord ID of user to register
        aimlabs_id (str): Aimlabs ID to associate with this Discord user
        timezone (str): Local timezone of the Discord user
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(
            insert(AimlabsTracking).values(
                user_id=user_id, aimlabs_id=aimlabs_id, timezone=timezone
            )
        )
