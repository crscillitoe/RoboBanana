from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, insert, update, DateTime
import logging
from datetime import datetime, timedelta

from db.models import EmojiReactions, EmojiReactionDelay, EmojiReactionTimes

LOG = logging.getLogger(__name__)

DEFAULT_EMOJI_REACTION_DELAY = 15 # Default delay for Robomoji reactions


def toggle_emoji_reaction(user_id: int, emoji: str, session: sessionmaker) -> bool:
    """Toggles emoji reaction for a given user

    Args:
        user_id (int): Discord User ID to add reaction to
        emoji (str): Discord \emoji_name representation of emoji to add to messages
        session (sessionmaker): Open DB session

    Returns:
        bool: True if emoji was toggled ON, False if toggled OFF
    """
    with session() as sess:
        result = sess.execute(
            select(EmojiReactions).where(
                EmojiReactions.user_id == user_id, EmojiReactions.emoji == emoji
            )
        ).first()
        if result is None:
            # Toggle emoji reaction ON
            sess.execute(insert(EmojiReactions).values(user_id=user_id, emoji=emoji))
            return True
        # Toggle emoji reaction OFF
        sess.execute(delete(EmojiReactions).where(EmojiReactions.id == result[0].id))
        return False


def get_reactions_for_user(user_id: int, session: sessionmaker) -> list[str]:
    """Get reactions to apply to a user's messages

    Args:
        user_id (int): Discord User ID to add reaction to
        session (sessionmaker): Open DB session

    Returns:
        list[str]: Emojis to apply to messages
    """
    with session() as sess:
        results = sess.execute(
            select(EmojiReactions).where(EmojiReactions.user_id == user_id)
        ).all()

        return [row[0].emoji for row in results]
    
def get_emoji_reaction_delay(session: sessionmaker) -> int:
    """
    Get Robomoji delay time 

    Returns:
        int: Delay time in seconds for Robomojis
    """
    with session() as sess:
        result = sess.query(EmojiReactionDelay).first()

        if result is None:
            sess.execute(insert(EmojiReactionDelay).values(delay_in_seconds=DEFAULT_EMOJI_REACTION_DELAY)) # Fallback default value of 15 seconds
            return DEFAULT_EMOJI_REACTION_DELAY
        
        return result.delay_in_seconds

def set_emoji_reaction_delay(delay_time: int, session: sessionmaker) -> int:
    """
    Set Robomoji delay time 

    Args:
        delay_time (int): Delay time in seconds for Robomojis
    """
    with session() as sess:
        result = sess.query(EmojiReactionDelay).first()

        if result is None:
            sess.execute(insert(EmojiReactionDelay).values(delay_in_seconds=delay_time))
            return delay_time

        existing_row: EmojiReactionDelay = result
        sess.execute(
            update(EmojiReactionDelay)
            .where(EmojiReactionDelay.id == existing_row.id)
            .values(delay_in_seconds=delay_time)
        )
        return delay_time
    
def get_emoji_reaction_last_used(user_id: int, session: sessionmaker) -> datetime:
    """
    Get DateTime of last Robomoji reaction

    Args:
        user_id (int): Discord User ID to add reaction to

    Returns:
        DateTime: DateTime of last Robomoji reaction for given user
    """
    with session() as sess:
        result = sess.execute(
            select(EmojiReactionTimes).where(EmojiReactionTimes.user_id == user_id)
        ).first()

        if result is None:
            sess.execute(insert(EmojiReactionTimes).values(user_id=user_id, last_reacted=datetime.now())) # First usage of Robomoji in new system by given user
            return datetime.now() - timedelta(minutes=5)
        
        emoji_reaction_time: EmojiReactionTimes = result[0]
        return emoji_reaction_time.last_reacted

def set_emoji_reaction_last_used(user_id: int, last_used: DateTime, session: sessionmaker):
    """
    Set DateTime of last Robomoji reaction

    Args:
        user_id (int): Discord User ID to add reaction to
        last_used (DateTime):  DateTime of most recently used Robomoji reaction
    """
    with session() as sess:
        result = sess.execute(
            select(EmojiReactionTimes).where(EmojiReactionTimes.user_id == user_id)
        ).first()

        if result is None:
            sess.execute(insert(EmojiReactionTimes).values(user_id=user_id, last_reacted=last_used)) # Extra check just in case row somehow doesn't exist

        existing_row: EmojiReactionTimes = result[0]
        sess.execute(
            update(EmojiReactionTimes)
            .where(EmojiReactionTimes.id == existing_row.id)
            .values(user_id=user_id, last_reacted=last_used)
        )