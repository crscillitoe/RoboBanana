from db.models import ChannelPoints, MorningPoints
from sqlalchemy import select, update, insert
from sqlalchemy.orm import sessionmaker
from datetime import timedelta, datetime
from config import Config
from discord import Role
from zoneinfo import ZoneInfo

import discord

MIN_ACCRUAL_TIME = timedelta(minutes=15)
MAX_ACCRUAL_WINDOW = timedelta(minutes=30)
MORNING_DELTA = timedelta(hours=10)
POINTS_PER_ACCRUAL = 50

ROLE_MULTIPLIERS: dict[str, int] = {
    int(Config.CONFIG["Discord"]["Tier1RoleID"]): 2,
    int(Config.CONFIG["Discord"]["GiftedTier1RoleID"]): 2,
    int(Config.CONFIG["Discord"]["Tier2RoleID"]): 3,
    int(Config.CONFIG["Discord"]["GiftedTier2RoleID"]): 3,
    int(Config.CONFIG["Discord"]["Tier3RoleID"]): 4,
    int(Config.CONFIG["Discord"]["GiftedTier3RoleID"]): 4,
}


def get_multiplier_for_user(roles: list[Role]) -> int:
    for role_id, multiplier in ROLE_MULTIPLIERS.items():
        role = discord.utils.get(roles, id=role_id)
        if role is not None:
            return multiplier
    return 1


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
            sess.execute(insert(MorningPoints).values(user_id=user_id, weekly_count=1))
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


def get_point_balance(user_id: int, session: sessionmaker) -> int:
    """Get the number of points a user has accrued

    Args:
        user_id (int): Discord user ID to give points to
        session (sessionmaker): Open DB session

    Returns:
        int: Number of points currently accrued
    """
    with session() as sess:
        result = sess.execute(
            select(ChannelPoints).where(ChannelPoints.user_id == user_id)
        ).first()
        if result is None:
            return 0

        channel_points: ChannelPoints = result[0]
        return channel_points.points


def withdraw_points(
    user_id: int, point_amount: int, session: sessionmaker
) -> tuple[bool, int]:
    """Withdraw points from user's current balance

    Args:
        user_id (int): Discord user ID to give points to
        point_amount (int): Number of points to withdraw
        session (sessionmaker): Open DB session

    Returns:
        tuple[bool, int]: True if points were successfully withdrawn. If so, return new balance
    """
    with session() as sess:
        result = sess.execute(
            select(ChannelPoints).where(ChannelPoints.user_id == user_id)
        ).first()
        if result is None:
            return False, -1

        channel_points: ChannelPoints = result[0]
        new_balance = channel_points.points - point_amount
        sess.execute(
            update(ChannelPoints)
            .where(ChannelPoints.user_id == user_id)
            .values(
                points=new_balance,
            )
        )
        return True, new_balance


def deposit_points(
    user_id: int, point_amount: int, session: sessionmaker
) -> tuple[bool, int]:
    """Deposit points into user's balance

    Args:
        user_id (int): Discord user ID to give points to
        point_amount (int): Number of points to withdraw
        session (sessionmaker): Open DB session

    Returns:
        tuple[bool, int]: True if points were successfully depisoted. If so, return new balance
    """
    with session() as sess:
        result = sess.execute(
            select(ChannelPoints).where(ChannelPoints.user_id == user_id)
        ).first()
        if result is None:
            return False, -1

        channel_points: ChannelPoints = result[0]
        new_balance = channel_points.points + point_amount
        sess.execute(
            update(ChannelPoints)
            .where(ChannelPoints.user_id == user_id)
            .values(
                points=new_balance,
            )
        )
        return True, new_balance


def accrue_channel_points(
    user_id: int, roles: list[Role], session: sessionmaker
) -> bool:
    """Accrues channel points for a given user

    Args:
        user_id (int): Discord user ID to give points to
        roles (list[int]): List of Discord Role IDs that user is assigned
        session (sessionmaker): Open DB session

    Returns:
        bool: True if points were awarded to the user
    """
    with session() as sess:
        result = sess.execute(
            select(ChannelPoints).where(ChannelPoints.user_id == user_id)
        ).first()
        if result is None:
            sess.execute(
                insert(ChannelPoints).values(user_id=user_id, points=POINTS_PER_ACCRUAL)
            )
            return True

        # Ensure points are not accruing on every message
        # Only award points once per hour
        channel_points: ChannelPoints = result[0]
        last_accrued: datetime = channel_points.timestamp
        now = datetime.now()
        time_difference = now - last_accrued

        if time_difference < MIN_ACCRUAL_TIME:
            return False

        updated_timestamp = now
        if time_difference < MAX_ACCRUAL_WINDOW:
            updated_timestamp = last_accrued + MIN_ACCRUAL_TIME

        points_to_accrue = POINTS_PER_ACCRUAL * get_multiplier_for_user(roles)
        sess.execute(
            update(ChannelPoints)
            .where(ChannelPoints.user_id == user_id)
            .values(
                points=channel_points.points + points_to_accrue,
                timestamp=updated_timestamp,
            )
        )
        return True
