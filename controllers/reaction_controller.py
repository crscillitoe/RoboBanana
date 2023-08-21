from discord import Message
from db import DB
from datetime import datetime, timedelta


class ReactionController:
    @staticmethod
    async def apply_reactions(message: Message):
        emojis = DB().get_reactions_for_user(message.author.id)
        if len(emojis) != 0:
            emoji_delay_seconds = DB().get_emoji_reaction_delay()
            last_reaction_datetime = DB().get_emoji_reaction_last_used(message.author.id)
            robomoji_allowed_datetime = last_reaction_datetime + timedelta(seconds=emoji_delay_seconds)
            if (robomoji_allowed_datetime <= datetime.now()):
                for emoji in emojis:
                    await message.add_reaction(emoji)
                DB().set_emoji_reaction_last_used(message.author.id, datetime.now())
