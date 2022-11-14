from datetime import datetime
from db.models import Prediction, PredictionEntry, PredictionSummary
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, insert, func
from typing import Optional


def create_prediction(
    guild_id: int,
    channel_id: int,
    message_id: int,
    description: str,
    option_one: str,
    option_two: str,
    end_time: datetime,
    session: sessionmaker,
) -> None:
    if has_ongoing_prediction(guild_id, session):
        raise Exception("There is already an ongoing prediction!")

    with session() as sess:
        sess.execute(
            insert(Prediction).values(
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=message_id,
                description=description,
                option_one=option_one,
                option_two=option_two,
                end_time=end_time,
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


def accepting_prediction_entries(guild_id: int, session: sessionmaker) -> bool:
    with session() as sess:
        stmt = (
            select(Prediction)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
            .where(Prediction.accepting_entries == True)
        )
        result = sess.execute(stmt).all()

    return len(result) > 0


def close_prediction(guild_id: int, session: sessionmaker):
    with session() as sess:
        sess.execute(
            update(Prediction)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
            .values(accepting_entries=False)
        )


def complete_prediction(guild_id: int, session: sessionmaker):
    with session() as sess:
        sess.execute(
            update(Prediction)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
            .values(ended=True, accepting_entries=False)
        )


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

def get_prediction_channel_id(guild_id: int, session: sessionmaker) -> Optional[int]:
    if not has_ongoing_prediction(guild_id, session):
        raise Exception("There is no ongoing prediction! You need to start a new one.")

    with session() as sess:
        stmt = (
            select(Prediction.channel_id)
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
    prediction_id = get_prediction_id(guild_id, session)
    with session() as sess:
        sess.execute(
            insert(PredictionEntry).values(
                prediction_id=prediction_id,
                user_id=user_id,
                channel_points=channel_points,
                guess=guess,
            )
        )


def get_user_prediction_entry(
    guild_id: int, user_id: int, session: sessionmaker
) -> Optional[PredictionEntry]:
    prediction_id = get_prediction_id(guild_id, session)
    with session() as sess:
        stmt = (
            select(PredictionEntry)
            .where(PredictionEntry.prediction_id == prediction_id)
            .where(PredictionEntry.user_id == user_id)
        )
        result = sess.execute(stmt).all()

    if len(result) == 0:
        return None

    return result[0][0]


def get_prediction_point_counts(
    guild_id: int, session: sessionmaker
) -> tuple[int, int]:
    # special case for immediately after prediction is created
    if not has_ongoing_prediction(guild_id, session):
        return (0, 0)

    prediction_id = get_prediction_id(guild_id, session)
    with session() as sess:
        stmt = (
            select(func.sum(PredictionEntry.channel_points))
            .select_from(PredictionEntry)
            .where(PredictionEntry.prediction_id == prediction_id)
            .where(PredictionEntry.guess == 0)
        )
        result_one = sess.execute(stmt).first()[0]
        if result_one is None:
            result_one = 0

        stmt = (
            select(func.sum(PredictionEntry.channel_points))
            .select_from(PredictionEntry)
            .where(PredictionEntry.prediction_id == prediction_id)
            .where(PredictionEntry.guess == 1)
        )
        result_two = sess.execute(stmt).first()[0]
        if result_two is None:
            result_two = 0

    return (int(result_one), int(result_two))


def get_prediction_entries_for_guess(
    guild_id: int, guess: int, session: sessionmaker
) -> list[PredictionEntry]:
    prediction_id = get_prediction_id(guild_id, session)
    with session() as sess:
        results = sess.execute(
            select(PredictionEntry)
            .where(PredictionEntry.prediction_id == prediction_id)
            .where(PredictionEntry.guess == guess)
        ).all()
        if len(results) == 0:
            return results

        return list(map(lambda result: result[0], results))


def get_prediction_summary(guild_id: int, session: sessionmaker) -> PredictionSummary:
    with session() as sess:
        stmt = (
            select(Prediction)
            .where(Prediction.guild_id == guild_id)
            .where(Prediction.ended == False)
        )
        result = sess.execute(stmt).all()
        if len(result) == 0:
            raise Exception(
                "There is no ongoing prediction! You need to start a new one."
            )
        prediction: Prediction = result[0][0]
        option_one_points, option_two_points = get_prediction_point_counts(
            guild_id, session
        )
        return PredictionSummary(
            prediction.description,
            prediction.option_one,
            prediction.option_two,
            option_one_points,
            option_two_points,
            prediction.end_time,
            prediction.accepting_entries,
        )
