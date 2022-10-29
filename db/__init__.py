from sqlalchemy import create_engine, select, update, insert, func
from sqlalchemy.orm import sessionmaker

from .models import Base, Raffle, RaffleEntry, RoleModifier

from config import Config

from datetime import datetime
from typing import Optional

class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        username = Config.CONFIG["MySQL"]["Username"]
        password = Config.CONFIG["MySQL"]["Password"]
        db_host = Config.CONFIG["MySQL"]["Host"]
        db_name = Config.CONFIG["MySQL"]["Name"]

        self.engine = create_engine(f"mysql+pymysql://{username}:{password}@{db_host}/{db_name}")
        self.session = sessionmaker(self.engine, autoflush=True, autocommit=True)

        Base.metadata.create_all(self.engine)

    def create_raffle(self, guild_id: int, message_id: int) -> None:
        if self.has_ongoing_raffle(guild_id):
            raise Exception("There is already an ongoing raffle!")

        with self.session() as sess:
            sess.execute(
                insert(Raffle)
                .values(guild_id=guild_id, message_id=message_id)
            )

    def create_raffle_entry(self, guild_id: int, user_id: int, tickets: int) -> None:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            sess.execute(
                insert(RaffleEntry)
                .values(raffle_id=raffle_id, user_id=user_id, tickets=tickets)
            )

    def get_user_raffle_entry(self, guild_id: int, user_id: int) -> RaffleEntry:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
                .where(RaffleEntry.user_id == user_id)
            )
            result = sess.execute(stmt).all()

        if len(result) == 0:
            return None

        return result[0][0]

    def get_raffle_entries(self, guild_id: int) -> list[RaffleEntry]:
        if not self.has_ongoing_raffle(guild_id):
            return []

        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(RaffleEntry)
                .join(Raffle, Raffle.id == RaffleEntry.raffle_id)
                .where(Raffle.id == raffle_id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
            )
            result = sess.execute(stmt).all()

        return [r[0] for r in result]

    def get_raffle_entry_count(self, guild_id: int) -> int:
        # special case for immediately after raffle is created
        if not self.has_ongoing_raffle(guild_id):
            return 0

        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(func.count("*"))
                .select_from(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
            )
            result = sess.execute(stmt).one()

        return result[0]

    def has_ongoing_raffle(self, guild_id: int) -> bool:
        with self.session() as sess:
            stmt = (
                select(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
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
                .where(Raffle.ended == False)
                .limit(1)
            )
            result = sess.execute(stmt).one()

        if len(result) == 0:
            return None

        return result[0]

    def get_raffle_id(self, guild_id: int) -> Optional[int]:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            stmt = (
                select(Raffle.id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .limit(1)
            )
            result = sess.execute(stmt).one()

        if len(result) == 0:
            return None

        return result[0]

    def close_raffle(self, guild_id: int, end_time: datetime) -> None:
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        with self.session() as sess:
            sess.execute(
                update(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .values(ended=True, end_time=end_time)
                .execution_options(synchronize_session="fetch")
            )

    def record_win(
        self, guild_id: int, user_ids: list[int]
    ) -> None:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            # for uid in user_ids:
            sess.execute(
                update(RaffleEntry)
                .where(RaffleEntry.raffle_id == raffle_id)
                .where(RaffleEntry.user_id.in_(user_ids))
                .values(winner=True)
                .execution_options(synchronize_session=False)
            )

    def clear_win(self, raffle_message_id: int) -> None:
        with self.session() as sess:
            sess.execute(
                update(Raffle)
                .where(Raffle.message_id == raffle_message_id)
                .where(Raffle.ended == True)
                .values(ended=False, end_time=None)
                .execution_options(synchronize_session="fetch")
            )

    def recent_winner_ids(self, guild_id: int) -> set[int]:
        # TODO: rewrite to read from raffle_entries and check date
        return set()

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

    def get_role_modifiers(self, guild_id: int) -> dict[int, int]:
        with self.session() as sess:
            stmt = (
                select(RoleModifier)
                .where(RoleModifier.guild_id == guild_id)
            )
            result = sess.execute(stmt).all()

        return {r[0].role_id: r[0].modifier for r in result}
