from models.transaction import Transaction
from db import DB
from config import YAMLConfig as Config

MAXIMUM_TRANSACTIONS = Config.CONFIG["Discord"]["PointsHistory"]["MaximumTransactions"]


class PointHistoryController:
    @staticmethod
    def record_transaction(transaction: Transaction):
        user_history = DB().get_transaction_history(transaction.user_id)
        if len(user_history) >= MAXIMUM_TRANSACTIONS:
            to_delete = user_history[MAXIMUM_TRANSACTIONS - 1 :]
            DB().delete_transactions(to_delete)
        DB().record_transaction(transaction)

    @staticmethod
    def get_transaction_history(user_id: int):
        return DB().get_transaction_history(user_id)
