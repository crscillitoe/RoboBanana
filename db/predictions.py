from db.models import Prediction, PredictionEntry
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, insert
from typing import Optional


def create_prediction(
    guild_id: int,
    message_id: int,
    option_one: str,
    option_two: str,
    session: sessionmaker,
) -> None:
    if has_ongoing_prediction(guild_id, session):
        raise Exception("There is already an ongoing prediction!")

    with session() as sess:
        sess.execute(
            insert(Prediction).values(
                guild_id=guild_id,
                message_id=message_id,
                option_one=option_one,
                option_two=option_two,
            )
        )


def has_ongoing_prediction(guild_id: int, session: sessionmaker) -> bool:
    with session() as sess:
        stmt = (
            select(Prediction)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
        )
        result = sess.execute(stmt).all()

    return len(result) > 0


def get_prediction_id(guild_id: int, session: sessionmaker) -> Optional[int]:
    if not has_ongoing_prediction(guild_id, session):
        raise Exception("There is no ongoing prediction! You need to start a new one.")

    with session() as sess:
        stmt = (
            select(Prediction.id)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
            .limit(1)
        )
        result = sess.execute(stmt).one()

    if len(result) == 0:
        return None

    return result[0]


def get_prediction_message_id(guild_id: int, session: sessionmaker) -> Optional[int]:
    if not has_ongoing_prediction(guild_id, session):
        raise Exception("There is no ongoing prediction! You need to start a new one.")

    with session() as sess:
        stmt = (
            select(Prediction.message_id)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
            .limit(1)
        )
        result = sess.execute(stmt).one()

    if len(result) == 0:
        return None

    return result[0]


def create_prediction_entry(
    guild_id: int, user_id: int, channel_points: int, guess: int, session: sessionmaker
) -> None:
    raffle_id = get_prediction_id(guild_id, session)
    with session() as sess:
        sess.execute(
            insert(PredictionEntry).values(
                raffle_id=raffle_id,
                user_id=user_id,
                channel_points=channel_points,
                guess=guess,
            )
        )


def get_user_prediction_entry(
    guild_id: int, user_id: int, session: sessionmaker
) -> PredictionEntry:
    raffle_id = get_prediction_id(guild_id)
    with session() as sess:
        stmt = (
            select(PredictionEntry)
            .where(PredictionEntry.raffle_id == raffle_id)
            .where(PredictionEntry.user_id == user_id)
        )
        result = sess.execute(stmt).all()

    if len(result) == 0:
        return None

    return result[0][0]
