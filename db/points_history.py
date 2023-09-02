from db.models import PointsHistory
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, delete, desc
from config import YAMLConfig as Config
from models.transaction import Transaction


def record_transaction(transaction: Transaction, session: sessionmaker):
    """Record transaction into points history respecting maximum
    maximum transaction limit

    Args:
        transaction (Transaction): Transaction data to record
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        sess.execute(
            insert(PointsHistory).values(
                user_id=transaction.user_id,
                points_delta=transaction.points_delta,
                starting_balance=transaction.starting_balance,
                ending_balance=transaction.ending_balance,
                reason=transaction.reason,
            )
        )


def get_transaction_history(user_id: int, session: sessionmaker):
    """Get transaction history for user

    Args:
        user_id (int): Discord User ID of user
        session (sessionmaker): Open DB session

    Returns:
        list[PointsHistory]: Up to MAXIMUM_TRANSACTIONS most recent point transactions
    """
    with session() as sess:
        results = sess.execute(
            select(PointsHistory)
            .where(PointsHistory.user_id == user_id)
            .order_by(desc(PointsHistory.timestamp))
        ).all()
        user_history: list[PointsHistory] = [row[0] for row in results]
        return user_history


def delete_transactions(transactions: list[PointsHistory], session: sessionmaker):
    """Delete transactions from PointsHistory

    Args:
        transactions (list[PointsHistory]): Transactions to delete
        session (sessionmaker): Open DB session
    """
    with session() as sess:
        to_delete = list(map(lambda transaction: transaction.id, transactions))
        sess.execute(delete(PointsHistory).where(PointsHistory.id.in_(to_delete)))
