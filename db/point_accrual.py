from db.models import ChannelPoints
from sqlalchemy import select, update, insert
from sqlalchemy.orm import sessionmaker
from datetime import timedelta, datetime
from config import Config
from discord import Role

import discord

MIN_ACCRUAL_TIME = timedelta(minutes=15)
MAX_ACCRUAL_WINDOW = timedelta(minutes=30)
POINTS_PER_ACCRUAL = 50

ROLE_MULTIPLIERS: dict[str, int] = {
    int(Config.CONFIG["Discord"]["Tier1RoleID"]): 2,
    int(Config.CONFIG["Discord"]["Tier2RoleID"]): 3,
    int(Config.CONFIG["Discord"]["Tier3RoleID"]): 4,
}


def get_multiplier_for_user(roles: list[Role]) -> int:
    for role_id, multiplier in ROLE_MULTIPLIERS.items():
        role = discord.utils.get(roles, id=role_id)
        if role is not None:
            return multiplier
    return 1


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
