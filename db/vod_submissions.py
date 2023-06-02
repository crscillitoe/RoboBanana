from datetime import datetime
from db.models import VodSubmission
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, func, delete
from sqlalchemy.dialects.mysql import Insert
from typing import Optional


def get_latest_timestamp(user_id: int, session: sessionmaker) -> int:
    """Get the latest timestamp of the users submitted VOD

    Args:
        user_id (int): Discord user ID
        session (sessionmaker): Open DB session

    Returns:
        datetime: Time most recent vod was submitted by user
    """
    with session() as sess:
        result = sess.execute(
            select(VodSubmission).where(VodSubmission.user_id == user_id)
        ).first()
        if result is None:
            return None

        submission: VodSubmission = result[0]
        return submission.timestamp


def reset_user(user_id: int, session: sessionmaker):
    with session() as sess:
        result = sess.execute(
            delete(VodSubmission).where(VodSubmission.user_id == user_id)
        )


def update_timestamp(user_id: int, session: sessionmaker):
    """Set the vod submission timestamp for the given user to now

    Args:
        user_id (int): Discord user ID
        session (sessionmaker): Open DB session
    """

    insert_stmt = Insert(VodSubmission).values(user_id=user_id, timestamp=func.now())

    on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(
        timestamp=insert_stmt.inserted.timestamp
    )

    with session() as sess:
        result = sess.execute(on_duplicate_key_stmt)
