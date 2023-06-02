from discord import Message
from db import DB


class ReactionController:
    @staticmethod
    async def apply_reactions(message: Message):
        emojis = DB().get_reactions_for_user(message.author.id)
        for emoji in emojis:
            await message.add_reaction(emoji)
