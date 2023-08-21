from datetime import datetime
from db.models import TempRoles
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, insert, update, func


def set_temprole(
    user_id: int,
    role_id: int,
    guild_id: int,
    expiration: datetime,
    session: sessionmaker,
):
    """Set temprole for user to specified duration, even if one exists already

    Args:
        user_id (int): Discord User ID to grant role to
        role_id (int): Role ID to grant to user
        guild_id (int): Discord Guild ID the user belongs to
        expiration (datetime): Expiration date of role
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        result = retrieve_temprole(user_id, role_id, session)
        if result is None:
            sess.execute(
                insert(TempRoles).values(
                    user_id=user_id,
                    role_id=role_id,
                    guild_id=guild_id,
                    expiration=expiration,
                )
            )
            return
        sess.execute(
            update(TempRoles)
            .where(TempRoles.user_id == user_id)
            .where(TempRoles.role_id == role_id)
            .values(expiration=expiration)
        )


def retrieve_temprole(
    user_id: int, role_id: int, session: sessionmaker
) -> TempRoles | None:
    """Retrieve temprole for user_id / role_id pairing

    Args:
        user_id (int): Discord User ID of user to grab temprole for
        role_id (int): Discord Role ID of role to grab temprole for
        session (sessionmaker): Open DB session

    Returns:
        TempRoles | None: None if no pairing exists, TempRoles otherwise
    """
    with session() as sess:
        result = sess.execute(
            select(TempRoles)
            .where(TempRoles.user_id == user_id)
            .where(TempRoles.role_id == role_id)
        ).first()
        if result is None:
            return None
        return result[0]


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


def get_temprole_users(
    role_id: int,
    guild_id: int,
    session: sessionmaker,
    offset: int = 0,
    limit: int = None,
) -> list[TempRoles]:
    """Get all users that have given temprole

    Args:
        role_id (int): Discord Role ID to grab users for
        guild_id (int): Guild ID to grab users for
        session (sessionmaker): Open DB Session
        offset (int, optional): Number of results to skip. Default is 0
        limit (int): Max number of results to return. Default is all results

    Returns:
        list[TempRoles]: All users that have given temprole
    """
    with session() as sess:
        results = sess.execute(
            select(TempRoles)
            .where(TempRoles.role_id == role_id)
            .where(TempRoles.guild_id == guild_id)
            .offset(offset)
            .limit(limit)
        ).all()

        if len(results) == 0:
            return results

        return list(map(lambda result: result[0], results))


def get_temprole_users_count(role_id: int, guild_id: int, session: sessionmaker) -> int:
    """Get number of users that have given temprole

    Args:
        role_id (int): Discord Role ID to grab users for
        guild_id (int): Guild ID to grab users for
        session (sessionmaker): Open DB Session

    Returns:
        int: Number of users that have given temprole
    """
    with session() as sess:
        count = sess.execute(
            select(func.count())
            .where(TempRoles.role_id == role_id)
            .where(TempRoles.guild_id == guild_id)
        ).scalar()

    return count
