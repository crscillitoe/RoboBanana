from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, insert
import logging

from db.models import EmojiReactions

LOG = logging.getLogger(__name__)


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
