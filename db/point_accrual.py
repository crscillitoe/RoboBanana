from db.models import ChannelPoints
from sqlalchemy import select, update, insert
from sqlalchemy.orm import sessionmaker
from datetime import timedelta, datetime
from config import YAMLConfig as Config
from discord import Role

import discord

MIN_ACCRUAL_TIME = timedelta(minutes=15)
MAX_ACCRUAL_WINDOW = timedelta(minutes=30)
POINTS_PER_ACCRUAL = 50


ROLE_MULTIPLIERS: dict[str, int] = {
    Config.CONFIG["Discord"]["Subscribers"]["Tier1Role"]: 2,
    Config.CONFIG["Discord"]["Subscribers"]["GiftedTier1Role"]: 2,
    Config.CONFIG["Discord"]["Subscribers"]["Tier2Role"]: 3,
    Config.CONFIG["Discord"]["Subscribers"]["GiftedTier2Role"]: 3,
    Config.CONFIG["Discord"]["Subscribers"]["Tier3Role"]: 4,
    Config.CONFIG["Discord"]["Subscribers"]["GiftedTier3Role"]: 4,
}


def get_multiplier_for_user(roles: list[Role]) -> int:
    for role_id, multiplier in sorted(
        ROLE_MULTIPLIERS.items(), key=lambda item: item[1], reverse=True
    ):
        role = discord.utils.get(roles, id=role_id)
        if role is not None:
            return multiplier
    return 1


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
