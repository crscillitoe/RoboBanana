from datetime import datetime, timedelta
from typing import Optional
from discord import Message
from db import DB
from config import Config

MESSAGE_BATCH_SIZE = int(Config.CONFIG["Discord"]["GoodMorningBatchSize"])
MAX_TIME_BETWEEN_RESPONSE = timedelta(seconds=5)
MESSAGE_EXPLANATION = "\n\nWhat's this message? <#1064317660084584619>"


class GoodMorningController:
    current_accruals = list()
    last_response: Optional[datetime] = None

    async def _send_accrual_responses(message: Message):
        response = "\n".join(GoodMorningController.current_accruals)
        response += MESSAGE_EXPLANATION
        await message.channel.send(response)
        GoodMorningController.last_response = message.created_at
        GoodMorningController.current_accruals = list()

    def _should_respond(message: Message):
        if GoodMorningController.last_response is None:
            GoodMorningController.last_response = message.created_at

        if len(GoodMorningController.current_accruals) == 0:
            return False

        if len(GoodMorningController.current_accruals) >= MESSAGE_BATCH_SIZE:
            return True

        time_passed = message.created_at - GoodMorningController.last_response
        if time_passed >= MAX_TIME_BETWEEN_RESPONSE:
            return True

        return False

    async def handle_response(message: Message):
        """Respond to good morning messages if requirements met

        Args:
            message (Message): Message in stream chat
        """
        if GoodMorningController._should_respond(message):
            await GoodMorningController._send_accrual_responses(message)

    async def accrue_good_morning(message: Message):
        """Accrue good morning message point

        Args:
            message (Message): "good morning" stream chat message
        """
        accrued = DB().accrue_morning_points(message.author.id)
        if not accrued:
            return

        points = DB().get_morning_points(message.author.id)
        response = f"Good morning {message.author.mention}! Your current weekly count is {points}!"
        GoodMorningController.current_accruals.append(response)
