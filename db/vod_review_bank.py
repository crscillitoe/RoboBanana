from typing import Optional
from db.models import VODReviewBank
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update
from config import YAMLConfig as Config

HOURS_PER_REVIEW = Config.CONFIG["Discord"]["VODReview"]["RewardHoursPerReview"]


def add_vod_review_balance(user_id: int, amount: int, session: sessionmaker):
    """Add VOD review balance for specified user

    Args:
        user_id (int): Discord User ID of user who performed review
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        result = get_vod_review_balance(user_id, session)
        if result is None:
            sess.execute(insert(VODReviewBank).values(user_id=user_id, balance=amount))
            return amount
        sess.execute(
            update(VODReviewBank)
            .where(VODReviewBank.user_id == user_id)
            .values(balance=result + amount)
        )
        return result + amount


def get_vod_review_balance(user_id: int, session: sessionmaker) -> Optional[int]:
    """Get VOD review balance for specified user

    Args:
        user_id (int): Discord User ID
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        result = sess.execute(
            select(VODReviewBank).where(VODReviewBank.user_id == user_id)
        ).first()
        if result is None:
            return None
        bank: VODReviewBank = result[0]
        return bank.balance


def reset_vod_review_balance(user_id: int, session: sessionmaker):
    """Reset VOD review balance to 0h for specified user

    Args:
        user_id (int): Discord User ID of user to reset balance for
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(
            update(VODReviewBank)
            .where(VODReviewBank.user_id == user_id)
            .values(balance=0)
        )
