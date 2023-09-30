import json
from controllers.overlay_controller import OverlayController
from discord import TextStyle, Interaction
from discord.ui import Modal, TextInput


class OverlayConfigurationModal(Modal, title="Configure overlay"):
    def __init__(self):
        super().__init__(timeout=None)
        self.configure_field = TextInput(
            label="Paste configuration JSON below",
            placeholder='{"title": "UNDERPEEL"}',
            style=TextStyle.paragraph,
            min_length=1,
            required=True,
        )
        self.add_item(self.configure_field)

    async def on_submit(self, interaction: Interaction):
        overlay_config = json.loads(self.configure_field.value)
        OverlayController.publish_overlay(overlay_config)
        await interaction.response.send_message(
            "Set configuration to provided config", ephemeral=True
        )
