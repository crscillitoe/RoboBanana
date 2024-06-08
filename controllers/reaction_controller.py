from discord import HTTPException, Message, Reaction
from db import DB
from datetime import datetime, timedelta
import logging
from config import YAMLConfig as Config

LOG = logging.getLogger(__name__)

DEFAULT_EMOJI_REACTION_DELAY = (
    15  # Default delay for Robomoji reactions if not set manually
)
CROWD_MUTE_EMOJI_ID = Config.CONFIG["Discord"]["CrowdMute"]["Emoji"]
CROWD_MUTE_THRESHOLD = Config.CONFIG["Discord"]["CrowdMute"]["Threshold"]
CROWD_MUTE_DURATION = Config.CONFIG["Discord"]["CrowdMute"]["Duration"]

CROWD_MUTE_ENABLED = True


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
                try:
                    await message.add_reaction(emoji)
                except HTTPException as e:
                    if e.code == 10014:
                        LOG.error(f"Emoji {emoji} does not exist, removing from DB.")
                        DB().toggle_emoji_reaction(message.author.id, emoji)
            DB().set_emoji_reaction_last_used(message.author.id, datetime.now())

    @staticmethod
    async def apply_crowd_mute(reaction: Reaction):
        if not CROWD_MUTE_ENABLED:
            return
        if isinstance(reaction.emoji, str):
            return
        if reaction.emoji.id != CROWD_MUTE_EMOJI_ID:
            return
        if reaction.count < CROWD_MUTE_THRESHOLD:
            return

        if reaction.count == CROWD_MUTE_THRESHOLD:
            is_timed_out = reaction.message.author.is_timed_out()
            mute_reason = (
                f"been crowd muted for {CROWD_MUTE_DURATION} minutes, likely due to asking:"
                " "
                " 1. An easily Googleable question"
                " "
                " 2. A question about aim (see <#1056639643443007659>)"
                " "
                " 3. A question answered directly within our <#1035739990413545492>."
            )

            mute_reason = (
                f"BLOWN UP BY A BOMB. RECOVERY WILL TAKE {CROWD_MUTE_DURATION} MINUTES."
            )

            if is_timed_out != True:
                await reaction.message.author.timeout(
                    timedelta(minutes=CROWD_MUTE_DURATION),
                    reason=f"You have {mute_reason}",
                )
            await reaction.message.reply(f"THIS USER GOT {mute_reason}")
