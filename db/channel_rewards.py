from db.models import ChannelReward
from sqlalchemy import select, update, insert
from sqlalchemy.orm import sessionmaker


def add_channel_reward(name: str, point_cost: int, session: sessionmaker):
    """Add new reward that can be redeemed for ChannelPoints

    Args:
        name (str): Name of channel reward
        point_cost (int): Number of ChannelPoints required to redeem
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(insert(ChannelReward).values(name=name, point_cost=point_cost))


def get_channel_rewards(session: sessionmaker) -> list[ChannelReward]:
    """Get all available channel rewards

    Args:
        session (sessionmaker): Open DB session

    Returns:
        list[ChannelReward]: All currently available channel rewards
    """
    with session() as sess:
        return sess.query(ChannelReward).all()
