from discord import TextStyle, Interaction
from discord.ui import Modal, TextInput
from db import DB


class AddRewardModal(Modal, title="Add new channel reward"):
    def __init__(self):
        super().__init__(timeout=None)
        self.name = TextInput(
            label="Name",
            placeholder="Name of new channel reward",
            required=True,
        )
        self.point_cost = TextInput(
            label="Point Cost",
            placeholder="The number of points required to redeem this reward",
            required=True,
            style=TextStyle.short,
            min_length=1,
        )

        self.add_item(self.name)
        self.add_item(self.point_cost)

    async def on_submit(self, interaction: Interaction):
        try:
            point_cost = int(self.point_cost.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid point cost for reward.", ephemeral=True
            )
            return

        DB().add_channel_reward(self.name.value, point_cost)
        await interaction.response.send_message(f"New reward added!", ephemeral=True)
