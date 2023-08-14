from datetime import datetime
from db.models import TempRoles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, insert, func


def write_temprole(
    user_id: int,
    role_id: int,
    guild_id: int,
    expiration: datetime,
    session: sessionmaker,
):
    """Write a temprole to the DB

    Args:
        user_id (int): Discord User ID to grant role to
        role_id (int): Role ID to grant to user
        guild_id (int): Discord Guild ID the user belongs to
        expiration (datetime): Expritation date of role
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(
            insert(TempRoles).values(
                user_id=user_id,
                role_id=role_id,
                guild_id=guild_id,
                expiration=expiration,
            )
        )


def delete_temprole(id: int, session: sessionmaker):
    """Remove temprole from database with corresponding id

    Args:
        id (int): Temprole ID to delete
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(delete(TempRoles).where(TempRoles.id == id))


def get_expired_roles(compare_time: datetime, session: sessionmaker) -> list[TempRoles]:
    """Get temproles which will expire by given time

    Args:
        compare_time (datetime): Time to compare temproles to
        session (sessionmaker): Open DB session

    Returns:
        list[TempRoles]: All temproles which will be expired by this time
    """
    with session() as sess:
        results = sess.execute(
            select(TempRoles).where(TempRoles.expiration < compare_time)
        ).all()

        if len(results) == 0:
            return results

        return list(map(lambda result: result[0], results))


def get_user_temproles(
    user_id: int, guild_id: int, session: sessionmaker
) -> list[TempRoles]:
    """Get all temproles assigned to user

    Args:
        user_id (int): Discord User ID to grab roles for
        guild_id (int): Guild ID to grab roles for
        session (sessionmaker): Open DB Session

    Returns:
        list[TempRoles]: All temproles assigned to user
    """
    with session() as sess:
        results = sess.execute(
            select(TempRoles)
            .where(TempRoles.user_id == user_id)
            .where(TempRoles.guild_id == guild_id)
        ).all()

        if len(results) == 0:
            return results

        return list(map(lambda result: result[0], results))
