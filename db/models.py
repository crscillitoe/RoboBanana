from datetime import datetime
import enum
from sqlalchemy import (
    BigInteger,
    SmallInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    VARCHAR,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RaffleType(enum.Enum):
    normal = 1
    anyone = 2


class PredictionChoice(enum.Enum):
    left = 0
    right = 1


class PredictionOutcome(enum.Enum):
    refund = -1
    left = 0
    right = 1


class PredictionSummary:
    def __init__(
        self,
        description: str,
        option_one: str,
        option_two: str,
        option_one_points: int,
        option_two_points: int,
        end_time: datetime,
        set_nickname: bool,
        accepting_entries: bool,
        ended: bool,
    ):
        self.description = description
        self.option_one = option_one
        self.option_two = option_two
        self.option_one_points = option_one_points
        self.option_two_points = option_two_points
        self.end_time = end_time
        self.set_nickname = set_nickname
        self.accepting_entries = accepting_entries
        self.ended = ended


class Raffle(Base):
    __tablename__ = "raffles"

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False, unique=True)
    ended = Column(Boolean, nullable=False, default=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    raffle_type = Column(Enum(RaffleType), default=RaffleType.normal)

    entries = relationship("RaffleEntry", back_populates="raffle")

    def __repr__(self):
        return (
            f"Raffle(id={self.id!r}, guild_id={self.guild_id!r},"
            f" message_id={self.message_id!r}, start_time={self.start_time!r},"
            f" end_time={self.end_time!r}, ended={self.ended!r})"
        )


class RaffleEntry(Base):
    __tablename__ = "raffle_entries"

    id = Column(Integer, primary_key=True)
    raffle_id = Column(Integer, ForeignKey("raffles.id"))
    user_id = Column(BigInteger, nullable=False)
    tickets = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, default=func.now())
    winner = Column(Boolean, nullable=False, default=False)

    raffle = relationship("Raffle", back_populates="entries")

    def __repr__(self):
        return (
            f"RaffleEntry(id={self.id!r}, raffle_id={self.raffle_id!r},"
            f" user_id={self.user_id!r}, tickets={self.tickets!r},"
            f" timestamp={self.timestamp!r}, winner={self.winner!r})"
        )


class RoleModifier(Base):
    __tablename__ = "role_modifiers"

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, nullable=True, unique=True)
    modifier = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"RoleModifier(id={self.id!r}, guild_id={self.guild_id!r},"
            f" role_id={self.role_id!r}, modifier={self.modifier!r})"
        )


class MorningPoints(Base):
    __tablename__ = "morning_points"
    user_id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    weekly_count = Column(Integer, nullable=False, default=0)
    total_count = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"MorningPoints(user_id={self.user_id!r},"
            f" weekly_count={self.weekly_count!r}, total_count={self.total_count!r},"
            f" timestamp={self.timestamp!r})"
        )


class VodSubmission(Base):
    __tablename__ = "vod_submissions"
    user_id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"VodSubmission(user_id={self.user_id!r}, timestamp={self.timestamp!r})"


class ChannelPoints(Base):
    __tablename__ = "channel_points"
    user_id = Column(BigInteger, primary_key=True)
    points = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"ChannelPoints(user_id={self.user_id!r}, points={self.points!r},"
            f" timestamp={self.timestamp!r})"
        )


class ChannelReward(Base):
    __tablename__ = "channel_rewards"
    id = Column(Integer, primary_key=True)
    point_cost = Column(Integer, nullable=False)
    name = Column(VARCHAR(100), nullable=False)

    def __repr__(self):
        return (
            f"ChannelReward(id={self.id!r}, point_cost={self.point_cost!r},"
            f" name={self.name!r})"
        )


class AllowRedemption(Base):
    __tablename__ = "allow_redemption"

    id = Column(Integer, primary_key=True)
    allowed = Column(Boolean, default=False)

    def __repr__(self):
        return f"AllowRedemption(id={self.id!r}, allowed={self.allowed!r})"


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False, unique=True)
    accepting_entries = Column(Boolean, nullable=False, default=True)
    ended = Column(Boolean, nullable=False, default=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    description = Column(VARCHAR(100), nullable=False)
    option_one = Column(VARCHAR(100), nullable=False)
    option_two = Column(VARCHAR(100), nullable=False)
    set_nickname = Column(Boolean, nullable=False, default=False)
    winning_option = Column(SmallInteger, nullable=True)

    entries = relationship("PredictionEntry", back_populates="prediction")

    def __repr__(self):
        return (
            f"Prediction(id={self.id!r}, guild_id={self.guild_id!r},"
            f" message_id={self.message_id!r}, start_time={self.start_time!r},"
            f" end_time={self.end_time!r}, ended={self.ended!r},"
            f" winning_option={self.winning_option!r})"
        )


class PredictionEntry(Base):
    __tablename__ = "prediction_entries"

    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"))
    user_id = Column(BigInteger, nullable=False)
    channel_points = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, default=func.now())
    guess = Column(Integer, nullable=False)

    prediction = relationship("Prediction", back_populates="entries")

    def __repr__(self):
        return (
            f"PredictionEntry(id={self.id!r}, prediction_id={self.prediction_id!r},"
            f" user_id={self.user_id!r}, channel_points={self.channel_points!r},"
            f" guess={self.guess!r})"
        )


class EmojiReactions(Base):
    __tablename__ = "emoji_reactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    emoji = Column(VARCHAR(100), nullable=False)

    def __repr__(self):
        return (
            f"EmojiReaction(id={self.id!r}, user_id={self.user_id!r},"
            f" emoji={self.emoji})"
        )


class EmojiReactionDelay(Base):
    __tablename__ = "emoji_reaction_delay"

    id = Column(Integer, primary_key=True)
    delay_in_seconds = Column(Integer, nullable=False)

    def __repr__(self):
        return (
            f"EmojiReactionDelay(id={self.id!r},"
            f" delay_in_seconds={self.delay_in_seconds!r})"
        )


class EmojiReactionTimes(Base):
    __tablename__ = "emoji_reaction_times"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    last_reacted = Column(DateTime, nullable=False)

    def __repr__(self):
        return (
            f"EmojiReactionTimes(id={self.id!r}, user_id={self.user_id!r},"
            f" last_reacted={self.last_reacted!r})"
        )


class TempRoles(Base):
    __tablename__ = "temproles"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    role_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    expiration = Column(DateTime, nullable=False)

    def __repr__(self):
        return (
            f"TempRole(id={self.id!r}, user_id={self.user_id!r},"
            f" role_id={self.role_id!r}, guild_id={self.guild_id!r},"
            f" expiration={self.expiration!r})"
        )


class VODReviewBank(Base):
    __tablename__ = "vod_review_bank"

    user_id = Column(BigInteger, primary_key=True, nullable=False)
    balance = Column(Integer, nullable=False)

    def __repr__(self):
        return f"VODReviewBank(id={self.user_id!r}, balance={self.balance!r})"


class PointsHistory(Base):
    __tablename__ = "points_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    points_delta = Column(Integer, nullable=False)
    starting_balance = Column(Integer, nullable=False)
    ending_balance = Column(Integer, nullable=False)
    reason = Column(VARCHAR(50), nullable=False)

    def __repr__(self):
        return (
            f"PointsHistory(id={self.id!r}, user_id={self.user_id!r},"
            f" timestamp={self.timestamp!r}, points_delta={self.points_delta!r},"
            f" starting_balance={self.starting_balance!r},"
            f" ending_balance={self.ending_balnce!r}, reason={self.reason!r})"
        )
