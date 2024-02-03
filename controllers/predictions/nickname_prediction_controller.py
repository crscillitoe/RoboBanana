from asyncio import tasks
from collections import deque
import logging
from typing import Dict
from discord import Forbidden, Guild, Member
from config import YAMLConfig as Config
from discord.ext import tasks

LOG = logging.getLogger(__name__)
MAX_QUEUE_SIZE = Config.CONFIG["Discord"]["Predictions"]["MaxNicknameQueue"]
ACCUMULATORS = {}


class NicknamePredictionController:

    @staticmethod
    def get_accumulator(prediction_id: int, guild: Guild):
        try:
            acc = ACCUMULATORS[prediction_id]
            if not acc:
                acc = NicknameAccumulator(prediction_id, guild)
                ACCUMULATORS[prediction_id] = acc
        except KeyError:
            acc = NicknameAccumulator(prediction_id, guild)
            ACCUMULATORS[prediction_id] = acc
        return acc


class NicknameAccumulator:

    def __init__(self, prediction_id: int, guild: Guild):
        self.id = prediction_id
        self.guild = guild
        self.loop_fails = 0
        self.reset_loop_fails = 0
        self.started = False

        self._queue = deque()
        self.queue_size = 0
        self._reset_queue = deque()
        self.reset_queue_size = 0

    def add(self, member: int, prepend: str):
        if self.queue_size < MAX_QUEUE_SIZE:
            self._queue.append((member, prepend))
            self.queue_size += 1

            if self.started == False:
                self.process_nicknames.start()
                self.started = True
            return self.queue_size
        else:
            return -1

    @tasks.loop(seconds=1)
    async def process_nicknames(self):
        member: Member = None
        prepend: str = ""

        if self.loop_fails >= 15:
            self.cancel()
            return

        if self.queue_size == 0:
            self.loop_fails += 1
            return

        while self.queue_size > 0:
            try:
                rename = self._queue.popleft()
                member = self.guild.get_member(rename[0])
                prepend = rename[1]

                if member.display_name.lower().startswith(prepend.lower()):
                    member = None

            except IndexError:  # Increment fail counter to eventually stop the loop
                self.loop_fails += 1
            finally:
                self.queue_size -= 1

            if not member:
                continue
            else:
                self.loop_fails = 0
                break

        if not member:
            self.loop_fails += 1
            return

        old_name = member.display_name
        split = old_name.split(" ")
        if (
            split[0].lower() != prepend.lower()
            and (len(old_name) + len(prepend) + 1) <= 32
        ):  # Only proceed if the user doesn't have the tag already and the tag would fit
            try:
                await member.edit(nick=f"{prepend} {old_name}")
                self._reset_queue.append((member.id, prepend))
                self.reset_queue_size += 1
            except (
                Forbidden
            ):  # This should only ever happen if we try to edit the Guild Owner
                LOG.error(
                    f"[NicknameAccumulator (PID: {self.id})] Couldn't set nickname of user {member.id}. We are forbidden from editing the member."
                )
            except Exception as e:
                LOG.error(
                    f"[NicknameAccumulator (PID: {self.id})] Couldn't set nickname of user {member.id}. {e}"
                )

    def cancel(self):
        self.process_nicknames.cancel()
        self.loop_fails = 0
        self.started = False

    @tasks.loop(seconds=1)
    async def process_reset(self):
        member: Member = None
        prepend: str = ""

        if self.reset_loop_fails >= 15:
            self.process_reset.cancel()
            return

        if self.reset_queue_size == 0:
            self.reset_loop_fails += 1
            return

        while self.reset_queue_size > 0:
            try:
                rename = self._reset_queue.popleft()
                member = self.guild.get_member(rename[0])
                prepend = rename[1]

            except IndexError:  # Increment fail counter to eventually stop the loop
                self.reset_loop_fails += 1
            finally:
                self.reset_queue_size -= 1

            if not member:
                continue
            else:
                self.reset_loop_fails = 0
                break

        if not member:
            self.reset_loop_fails += 1
            return

        old_name = member.display_name
        split = old_name.split(" ")
        if (
            split[0].lower() == prepend.lower()
        ):  # Only proceed if the user has the tag already
            try:
                await member.edit(nick=old_name.replace(f"{prepend}", "", 1))
            except (
                Forbidden
            ):  # This should only ever happen if we try to edit the Guild Owner
                LOG.error(
                    f"[NicknameAccumulator (PID: {self.id})] Couldn't reset nickname of user {member.id}. We are forbidden from editing the member."
                )
            except Exception as e:
                LOG.error(
                    f"[NicknameAccumulator (PID: {self.id})] Couldn't reset nickname of user {member.id}. {e}"
                )
