from threading import Thread
from typing import Optional
from discord import (
    Attachment,
    app_commands,
    Interaction,
    Client,
)
import logging
from enum import Enum
from discord.app_commands.errors import AppCommandError, CheckFailure
from config import YAMLConfig as Config

from controllers.overlay_controller import OverlayController
from views.overlay.configure_modal import OverlayConfigurationModal

LOG = logging.getLogger(__name__)

MOD_ROLE = Config.CONFIG["Discord"]["Roles"]["Mod"]
# these are hardcoded until raze to radiant is over, or config file changes are allowed
# for testing on own setup, these need to be changed to your appropriate IDs
# HIDDEN_MOD_ROLE should be 1040337265790042172 when committing and refers to the Mod (Role Hidden)
HIDDEN_MOD_ROLE = 1040337265790042172


class TextFields(Enum):
    title = "title"
    headerLeft = "headerLeft"
    headerRight = "headerRight"
    sideBannerTextOne = "sideBannerTextOne"
    sideBannerTextTwo = "sideBannerTextTwo"
    sideBannerTextThree = "sideBannerTextThree"


class MediaFields(Enum):
    title = "title"
    headerIcon = "headerIcon"
    sideBannerIcon = "sideBannerIcon"
    backgroundVideo = "backgroundVideo"
    preRollVideo = "preRollVideo"
    timerBackground = "timerBackground"


class ListFields(Enum):
    scrollingText = "scrollingText"
    scrollingTextColors = "scrollingTextColors"


class AllFields(Enum):
    title = "title"
    timer = "timer"
    headerLeft = "headerLeft"
    headerRight = "headerRight"
    scrollingText = "scrollingText"
    scrollingTextColors = "scrollingTextColors"
    sideBannerTextOne = "sideBannerTextOne"
    sideBannerTextTwo = "sideBannerTextTwo"
    sideBannerTextThree = "sideBannerTextThree"
    headerIcon = "headerIcon"
    sideBannerIcon = "sideBannerIcon"
    backgroundVideo = "backgroundVideo"
    preRollVideo = "preRollVideo"
    timerBackground = "timerBackground"


class FieldType(str, Enum):
    TEXT = "text"
    MEDIA = "media"


class Switch(Enum):
    on = "on"
    off = "off"


@app_commands.guild_only()
class OverlayCommands(app_commands.Group, name="overlay"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="set_text")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(field="Overlay field to set")
    @app_commands.describe(text="Text to set field to")
    @app_commands.describe(color="Color of text")
    async def set_text(
        self, interaction: Interaction, field: TextFields, text: str, color: str = None
    ):
        """Set overlay text field to specified value"""
        OverlayController.publish_overlay(
            {field.value: {"type": FieldType.TEXT, "value": text, "color": color}}
        )
        await interaction.response.send_message(
            "Overlay text update sent!", ephemeral=True
        )

    @app_commands.command(name="set_media")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(field="Overlay field to set")
    @app_commands.describe(media_url="URL of image to send to frontend")
    @app_commands.describe(media="Attachment image to send to frontend")
    async def set_media(
        self,
        interaction: Interaction,
        field: MediaFields,
        media_url: Optional[str] = None,
        media: Optional[Attachment] = None,
    ):
        """Set overlay image field to provided image"""
        if media is not None:
            media_url = media.url

        OverlayController.publish_overlay(
            {field.value: {"type": FieldType.MEDIA, "source": media_url}}
        )
        await interaction.response.send_message(
            "Overlay image update sent!", ephemeral=True
        )

    @app_commands.command(name="set_list")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(field="Overlay field to set")
    @app_commands.describe(csv="Comma separated string of values")
    async def set_list(self, interaction: Interaction, field: ListFields, csv: str):
        """Set overlay list field to specified value"""
        values = csv.split(",")
        OverlayController.publish_overlay({field.value: values})
        await interaction.response.send_message(
            "Overlay list update sent!", ephemeral=True
        )

    @app_commands.command(name="clear_field")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(field="Overlay field to set")
    async def clear_field(self, interaction: Interaction, field: AllFields):
        """Clear value of field off overlay"""
        OverlayController.publish_overlay({field.value: None})
        await interaction.response.send_message(
            "Overlay clear update sent!", ephemeral=True
        )

    @app_commands.command(name="timer")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(duration="Duration in seconds of timer")
    @app_commands.describe(color="Color of text")
    async def timer(self, interaction: Interaction, duration: int, color: str = None):
        """Start timer on overlay for specified seconds"""
        OverlayController.publish_overlay(
            {"timer": {"duration": duration, "color": color}}
        )
        await interaction.response.send_message("Overlay update sent!", ephemeral=True)

    @app_commands.command(name="toggle")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    @app_commands.describe(switch="On/Off")
    async def toggle_overlay(self, interaction: Interaction, switch: Switch):
        """Toggle overlay to be on or off"""
        display = True
        if switch == Switch.off:
            display = False

        OverlayController.publish_overlay({"display": display})
        await interaction.response.send_message(
            f"Overlay toggled {switch.value}!", ephemeral=True
        )

    @app_commands.command(name="configure")
    @app_commands.checks.has_any_role(MOD_ROLE, HIDDEN_MOD_ROLE)
    async def configure(self, interaction: Interaction):
        """Paste JSON configuration for overlay directly into modal"""
        await interaction.response.send_modal(OverlayConfigurationModal())
