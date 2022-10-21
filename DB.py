from __future__ import annotations
from datetime import datetime, timedelta, timezone
import discord
import os
import sqlite3
from typing import Optional


class DB:

    __instance = None
    __instantiation_key = "YAY_SINGLETON_HACKS_IN_PYTHON"

    @classmethod
    def get(cls):
        if cls.__instance is None:
            cls.__instance = DB(instantiation_key=DB.__instantiation_key)
        return cls.__instance

    def __init__(self, instantiation_key=None):
        assert (
            instantiation_key == DB.__instantiation_key
        ), "Use DB.get() to connect to the database"
        self.conn = sqlite3.connect(os.environ.get("DB_PATH"))

    def create_raffle(self, guild_id: int, message_id: int) -> None:
        c = self.conn.cursor()
        if self.has_ongoing_raffle(guild_id):
            raise Exception("There is already an ongoing raffle!")

        c.execute(
            'INSERT INTO "raffles" (guild_id, message_id) VALUES (?, ?)',
            (
                guild_id,
                message_id,
            ),
        )
        self.conn.commit()
        c.close()

    def get_raffle_message_id(self, guild_id: int) -> Optional[int]:
        c = self.conn.cursor()
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        c.execute(
            'SELECT message_id FROM "raffles" WHERE "guild_id"=?',
            (guild_id,),
        )
        result = c.fetchone()
        if result is None:
            return None
        return result[0]

    def has_ongoing_raffle(self, guild_id: int) -> bool:
        c = self.conn.cursor()
        c.execute('SELECT rowid FROM "raffles" WHERE "guild_id"=?', (guild_id,))
        result = c.fetchone()
        return result is not None

    def close_raffle(self, guild_id: int) -> None:
        c = self.conn.cursor()
        if not self.has_ongoing_raffle(guild_id):
            raise Exception("There is no ongoing raffle! You need to start a new one.")

        c.execute(
            'DELETE FROM "raffles" WHERE "guild_id"=?',
            (guild_id,),
        )
        self.conn.commit()
        c.close()

    def record_win(
        self, guild_id: int, message_id: int, *users: discord.Member
    ) -> None:
        c = self.conn.cursor()
        values = list(map(lambda user: (guild_id, message_id, user.id), users))
        c.executemany(
            'INSERT INTO "past_wins" (guild_id, message_id, user_id) VALUES (?, ?, ?)',
            values,
        )
        self.conn.commit()
        c.close()

    def clear_wins(self, guild_id: int, message_id: int) -> None:
        c = self.conn.cursor()
        c.execute(
            'DELETE FROM "past_wins" WHERE guild_id = ? AND message_id = ?',
            (
                guild_id,
                message_id,
            ),
        )
        self.conn.commit()
        c.close()

    def recent_winner_ids(self, guild_id: int) -> set[int]:
        c = self.conn.cursor()
        c.execute(
            (
                'SELECT DISTINCT user_id FROM "past_wins" WHERE guild_id = ?'
                "ORDER BY id DESC LIMIT 6"
            ),
            (guild_id,),
        )
        results = c.fetchall()
        winners = set()
        for result in results:
            winners.add(int(result[0]))
        return winners

    def past_week_winner_ids(self, guild_id: int) -> set[int]:
        # Discord uses a snowflake ID scheme which stores the UTC timestamp
        # So rather than need to store a separate timestamp column, we can
        # filter on the ID prefix!
        one_week_ago = int(
            (datetime.now(tz=timezone.utc) - timedelta(days=7)).timestamp() * 1000
        )
        discord_timestamp = one_week_ago - 1420070400000  # Discord epoch
        min_snowflake = discord_timestamp << 22

        c = self.conn.cursor()
        c.execute(
            (
                'SELECT DISTINCT user_id FROM "past_wins" WHERE guild_id = ? '
                "AND message_id > ?"
            ),
            (
                guild_id,
                min_snowflake,
            ),
        )
        results = c.fetchall()
        winners = set()
        for result in results:
            winners.add(int(result[0]))
        return winners

    def all_winner_ids(self, guild_id: int) -> set[int]:
        c = self.conn.cursor()
        c.execute(
            'SELECT DISTINCT user_id FROM "past_wins" WHERE guild_id = ?',
            (guild_id,),
        )
        results = c.fetchall()
        winners = set()
        for result in results:
            winners.add(int(result[0]))
        return winners

    def win_counts(self, guild_id: int) -> dict[int, int]:
        c = self.conn.cursor()
        c.execute(
            (
                'SELECT user_id, COUNT(*) as num_wins FROM "past_wins"'
                "WHERE guild_id = ? GROUP BY user_id"
            ),
            (guild_id,),
        )
        results = c.fetchall()
        winners = {}
        for result in results:
            winners[int(result[0])] = int(result[1])
        return winners

    def eligible_role_ids(self, guild_id: int) -> set[int]:
        c = self.conn.cursor()
        c.execute(
            'SELECT DISTINCT role_id FROM "eligible_roles" WHERE guild_id = ?',
            (guild_id,),
        )
        results = c.fetchall()
        role_ids = set()
        for result in results:
            role_ids.add(int(result[0]))
        return role_ids