from sqlalchemy import create_engine, select, delete, func
from sqlalchemy.orm import sessionmaker

from .models import Base, EligibleRole, Raffle, Win

from datetime import datetime, timedelta, timezone
from discord import Member
from typing import Optional

DB_NAME = 'raffle.db'

class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.engine = create_engine(f"sqlite:///{DB_NAME}")
        self.session = sessionmaker(self.engine)

        Base.metadata.create_all(self.engine)

    def create_raffle(self, guild_id: int, message_id: int) -> None:
        if self.has_ongoing_raffle(guild_id):
            raise Exception("There is already an ongoing raffle!")

        with self.session() as sess:
            raffle = Raffle(guild_id=guild_id, message_id=message_id)
            sess.add(raffle)
            sess.commit()

    def has_ongoing_raffle(self, guild_id: int) -> bool:
        with self.session() as sess:
            stmt = (
                select(Raffle)
                .where(Raffle.guild_id == guild_id)
            )
            result = sess.execute(stmt).all()

        return len(result) > 0

    def get_raffle_message_id(self, guild_id: int) -> Optional[int]:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            stmt = (
                select(Raffle.message_id)
                .where(Raffle.guild_id == guild_id)
            )
            result = sess.execute(stmt).all()

        if len(result) == 0:
            return None

        return result[0][0]

    def close_raffle(self, guild_id: int) -> None:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            sess.execute(delete(Raffle).where(Raffle.guild_id == guild_id))
            sess.commit()

    def record_win(
        self, guild_id: int, message_id: int, *users: Member
    ) -> None:
        with self.session() as sess:
            values = list(map(lambda user: Win(guild_id=guild_id, message_id=message_id, user_id=user.id), users))
            sess.add_all(values)
            sess.commit()

    def clear_wins(self, guild_id: int, message_id: int) -> None:
        with self.session() as sess:
            sess.execute(
                delete(Win)
                .where(Win.guild_id == guild_id)
                .where(Win.message_id == message_id)
            )
            sess.commit()

    def recent_winner_ids(self, guild_id: int) -> set[int]:
        with self.session() as sess:
            stmt = (
                select(Win.user_id)
                .distinct()
                .where(Win.guild_id == guild_id)
                .order_by(Win.id.desc())
                .limit(6)
            )

            result = sess.execute(stmt).all()

        return {r[0] for r in result}

    def past_week_winner_ids(self, guild_id: int) -> set[int]:
        # Discord uses a snowflake ID scheme which stores the UTC timestamp
        # So rather than need to store a separate timestamp column, we can
        # filter on the ID prefix!
        one_week_ago = int(
            (datetime.now(tz=timezone.utc) - timedelta(days=7)).timestamp() * 1000
        )
        discord_timestamp = one_week_ago - 1420070400000  # Discord epoch
        min_snowflake = discord_timestamp << 22

        with self.session() as sess:
            stmt = (
                select(Win.user_id)
                .distinct()
                .where(Win.guild_id == guild_id)
                .where(Win.message_id > min_snowflake)
            )
            result = sess.execute(stmt).all()

        return {r[0] for r in result}

    def all_winner_ids(self, guild_id: int) -> set[int]:
        with self.session() as sess:
            stmt = (
                select(Win.user_id)
                .distinct()
                .where(Win.guild_id == guild_id)
            )
            result = sess.execute(stmt).all()

        return {r[0] for r in result}


    def win_counts(self, guild_id: int) -> dict[int, int]:
        with self.session() as sess:
            stmt = (
                select(Win.user_id, func.count("*").label("num_wins"))
                .where(Win.guild_id == guild_id)
                .group_by(Win.user_id)
            )
            result = sess.execute(stmt).all()

        return {user_id: wins for user_id, wins in result}

    def eligible_role_ids(self, guild_id: int) -> set[int]:
        with self.session() as sess:
            stmt = (
                select(EligibleRole.role_id)
                .where(EligibleRole.guild_id == guild_id)
            )
            result = sess.execute(stmt).all()

        return {r[0] for r in result}
