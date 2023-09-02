from dataclasses import dataclass


@dataclass
class Transaction:
    """Point Transaction Metadata"""

    user_id: int
    points_delta: int
    starting_balance: int
    ending_balance: int
    reason: str
