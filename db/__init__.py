from datetime import datetime
from sqlalchemy import create_engine, select, update, insert, func
from sqlalchemy.orm import sessionmaker
from typing import Optional

from .models import Base, Raffle, RaffleEntry, RoleModifier, RaffleType
from config import Config


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

        self.engine = create_engine(
            f"mysql+pymysql://{username}:{password}@{db_host}/{db_name}"
        )
        self.session = sessionmaker(self.engine, autoflush=True, autocommit=True)

        Base.metadata.create_all(self.engine)

    def create_raffle(
        self, guild_id: int, message_id: int, raffle_type: RaffleType
    ) -> None:
        if self.has_ongoing_raffle(guild_id):
            raise Exception("There is already an ongoing raffle!")

        with self.session() as sess:
            sess.execute(
                insert(Raffle).values(
                    guild_id=guild_id, message_id=message_id, raffle_type=raffle_type
                )
            )

    def create_raffle_entry(self, guild_id: int, user_id: int, tickets: int) -> None:
        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            sess.execute(
                insert(RaffleEntry).values(
                    raffle_id=raffle_id, user_id=user_id, tickets=tickets
                )
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

    def get_recent_win_stats(
        self, guild_id: int, user_id: int, after: datetime
    ) -> tuple[int, datetime]:
        """
        Query how many (normal) raffle wins a :user_id has had within a :guild_id since :after

        Returns wins since :after and the date they last won
        """
        with self.session() as sess:
            stmt = (
                select(func.count("*"), func.max(RaffleEntry.timestamp))
                .select_from(RaffleEntry)
                .join(Raffle)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == True)
                .where(Raffle.raffle_type == RaffleType.normal)
                .where(RaffleEntry.winner == True)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.end_time > after)
            )

            result = sess.execute(stmt).one()

        return result

    def get_raffle_entries(self, guild_id: int) -> list[RaffleEntry]:
        if not self.has_ongoing_raffle(guild_id):
            return []

        raffle_id = self.get_raffle_id(guild_id)
        with self.session() as sess:
            stmt = (
                select(RaffleEntry)
                .join(Raffle)
                .where(Raffle.id == raffle_id)
                .where(Raffle.guild_id == guild_id)
                .where(Raffle.ended == False)
                .where(RaffleEntry.winner == False)
            )
            result = sess.execute(stmt).all()

        return [r[0] for r in result]

    def get_loss_streak_for_user(self, user_id: int) -> int:
        """
        Fetch the current number of consecutive losses since the last win
        """

        with self.session() as sess:
            # get the most recent raffle entry with MAX(id)
            subquery = (
                select(func.ifnull(func.max(RaffleEntry.id), 0).label("last_win_id"))
                .join(Raffle)
                .where(RaffleEntry.winner == True)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.raffle_type == RaffleType.normal)
                .subquery()
            )

            # count all losses for the same user after the last winning entry
            stmt = (
                select(func.count("*"))
                .select_from(RaffleEntry)
                .join(Raffle)
                .where(RaffleEntry.id > subquery.c.last_win_id)
                .where(RaffleEntry.winner == False)
                .where(RaffleEntry.user_id == user_id)
                .where(Raffle.raffle_type == RaffleType.normal)
            )
            result = sess.execute(stmt).one()

        return result[0]

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

    def record_win(self, guild_id: int, user_ids: list[int]) -> None:
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
            # TODO: do we want to enable this?
            # clear winner status from previous entries, so anyone can win again
            # sess.execute(
            #     update(RaffleEntry)
            #     .values(winner=False)
            #     .where(RaffleEntry.raffle_id == Raffle.id)
            #     .where(Raffle.message_id == raffle_message_id)
            #     .where(Raffle.ended == True)
            #     .execution_options(synchronize_session="fetch")
            # )
            sess.execute(
                update(Raffle)
                .values(ended=False, end_time=None)
                .where(Raffle.message_id == raffle_message_id)
                .where(Raffle.ended == True)
                .execution_options(synchronize_session="fetch")
            )

    def get_role_modifiers(self, guild_id: int) -> dict[int, int]:
        with self.session() as sess:
            stmt = select(RoleModifier).where(RoleModifier.guild_id == guild_id)
            result = sess.execute(stmt).all()

        return {r[0].role_id: r[0].modifier for r in result}
