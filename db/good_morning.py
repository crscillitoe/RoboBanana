from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, insert
from zoneinfo import ZoneInfo

from db.models import MorningPoints
from config import YAMLConfig as Config


MORNING_DELTA = timedelta(hours=10)
MORNING_REWARD_REQUIREMENT = Config.CONFIG["Discord"]["GoodMorning"][
    "RewardRequirement"
]
RESET_TIMESTAMP = datetime(year=1970, month=1, day=1)


def accrue_morning_points(user_id: int, session: sessionmaker) -> bool:
    """Accrues morning greeting points for a given user

    Args:
        user_id (int): Discord user ID to give points to
        session (sessionmaker): Open DB session

    Returns:
        bool: True if points were awarded to the user
    """
    with session() as sess:
        result = sess.execute(
            select(MorningPoints).where(MorningPoints.user_id == user_id)
        ).first()
        if result is None:
            sess.execute(
                insert(MorningPoints).values(
                    user_id=user_id, weekly_count=1, total_count=1
                )
            )
            return True

        # Ensure points are not accruing on every message
        # Only award points once per stream
        morning_points: MorningPoints = result[0]
        last_accrued: datetime = morning_points.timestamp
        now = datetime.now()
        time_difference = now - last_accrued

        if time_difference < MORNING_DELTA:
            return False

        updated_timestamp = now

        sess.execute(
            update(MorningPoints)
            .where(MorningPoints.user_id == user_id)
            .values(
                weekly_count=morning_points.weekly_count + 1,
                total_count=morning_points.total_count + 1,
                timestamp=updated_timestamp,
            )
        )
        return True


def get_morning_points(user_id: int, session: sessionmaker) -> int:
    """Get the number of morning greetings a user has accrued

    Args:
        user_id (int): Discord user ID to give a morning greeting to
        session (sessionmaker): Open DB session

    Returns:
        int: Number of morning greetings currently awarded
    """
    with session() as sess:
        result = sess.execute(
            select(MorningPoints).where(MorningPoints.user_id == user_id)
        ).first()

    if result is None:
        return 0

    morning_points: MorningPoints = result[0]
    return morning_points.weekly_count


def get_today_morning_count(session: sessionmaker) -> int:
    """Get the number of users which have said good morning today

    Args:
        session (sessionmaker): Open DB session

    Returns:
        int: Number of users who have said good morning today
    """
    stream_start = datetime.utcnow().replace(
        hour=6, minute=0, second=0, tzinfo=ZoneInfo("America/Los_Angeles")
    )
    with session() as sess:
        count = (
            sess.query(MorningPoints)
            .filter(MorningPoints.timestamp > stream_start)
            .count()
        )
        return count


def get_morning_reward_winners(session: sessionmaker) -> list[int]:
    """Get the Discord User IDs of all users who earned good morning reward

    Args:
        session (sessionmaker): Open DB session

    Returns:
        list[int]: Discord User IDs of users to reward
    """
    with session() as sess:
        result = sess.execute(
            select(MorningPoints.user_id).where(
                MorningPoints.weekly_count >= MORNING_REWARD_REQUIREMENT
            )
        ).all()

    if result is None:
        return []

    return [row[0] for row in result]


def reset_all_morning_points(session: sessionmaker):
    """Set weekly_count to 0 for all users

    Args:
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(
            update(MorningPoints).values(weekly_count=0, timestamp=RESET_TIMESTAMP)
        )


def manual_increment_morning_points(value: int, session: sessionmaker):
    """Manually increment ALL USERS' morning points totals

    Args:
        value (int): Amount to increment users' morning points total by
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.query(MorningPoints).update(
            {
                MorningPoints.weekly_count: MorningPoints.weekly_count + value,
                MorningPoints.total_count: MorningPoints.total_count + value,
            }
        )
