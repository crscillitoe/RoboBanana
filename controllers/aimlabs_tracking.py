from discord import User
from db import DB


class AimlabsTrackingController:
    def register_user(user: User, aimlabs_id: str):
        DB().register_user(user.id, aimlabs_id)
