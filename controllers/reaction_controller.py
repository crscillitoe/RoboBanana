from discord import Message
from db import DB
from datetime import datetime, timedelta
import logging

LOG = logging.getLogger(__name__)

DEFAULT_EMOJI_REACTION_DELAY = (
    15  # Default delay for Robomoji reactions if not set manually
)


class ReactionController:
    """
    Applies configured reactions to messages sent by
    specified users
    """

    @staticmethod
    async def apply_reactions(message: Message):
        """
        Lookup configured reactions for the provided message author and apply them
        """
        emojis = DB().get_reactions_for_user(message.author.id)
        if len(emojis) == 0:
            return  # prevents further DB calls if user does not have any Robomojis

        db_emoji_delay = DB().get_emoji_reaction_delay()
        emoji_delay_seconds = (
            db_emoji_delay
            if db_emoji_delay != None
            else DEFAULT_EMOJI_REACTION_DELAY  # handles case if delay has not been set yet
        )

        last_reaction_datetime = DB().get_emoji_reaction_last_used(message.author.id)

        robomoji_allowed_datetime = (
            last_reaction_datetime or datetime.now()
        ) + timedelta(
            seconds=emoji_delay_seconds
        )  # handles case on user's first message in new system
        if (
            last_reaction_datetime
            == None  # handles case on user's first message in new system
            or robomoji_allowed_datetime <= datetime.now()
        ):
            for emoji in emojis:
                await message.add_reaction(emoji)
            DB().set_emoji_reaction_last_used(message.author.id, datetime.now())
