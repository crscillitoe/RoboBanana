from discord import ButtonStyle, Interaction
from discord.ui import Button, View
from datetime import datetime
from controllers.raffle_controller import RaffleController
from db import DB, RaffleType
import discord

from .raffle_embed import RaffleEmbed
from .redo_raffle_modal import RedoRaffleModal


class RaffleView(View):
    def __init__(
        self, parent: RaffleEmbed, num_winners: int, raffle_type: RaffleType
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        self.num_winners = num_winners
        self.raffle_type = raffle_type

        self.enter_raffle_button = Button(
            label="Enter Raffle",
            style=ButtonStyle.blurple,
            custom_id="raffle_view:enter_button",
        )
        self.enter_raffle_button.callback = self.enter_raffle_onclick
        self.add_item(self.enter_raffle_button)

        self.end_raffle_button = Button(
            label="End Raffle",
            style=ButtonStyle.red,
            custom_id="raffle_view:end_button",
        )
        self.end_raffle_button.callback = self.end_raffle_onclick
        self.add_item(self.end_raffle_button)

        self.redo_raffle_button = Button(
            label="Redo Raffle",
            style=ButtonStyle.secondary,
            disabled=True,
            custom_id="raffle_view:redo_button",
        )
        self.redo_raffle_button.callback = self.redo_raffle_onclick
        self.add_item(self.redo_raffle_button)

    def has_role(self, role_name: str, interaction: Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=role_name)
        return role is not None

    async def enter_raffle_onclick(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        guild_id = interaction.guild.id
        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.followup.send("This raffle is no longer active!")
            return

        user = interaction.user
        if DB().get_user_raffle_entry(guild_id, user.id) is not None:
            await interaction.followup.send(
                "You have already entered this raffle!", ephemeral=True
            )
            return

        # Mods can always enter a raffle, anyone can enter in "anyone" raffle type
        if (
            not self.has_role("Mod", interaction)
            and self.raffle_type == RaffleType.normal
        ):
            eligible, ineligibility_message = RaffleController.eligible_for_raffle(
                guild_id, user
            )
            if not eligible:
                await interaction.followup.send(
                    ineligibility_message,
                    ephemeral=True,
                )
                return

        tickets = RaffleController.get_tickets(guild_id, user, self.raffle_type)
        DB().create_raffle_entry(guild_id, user.id, tickets)

        self.parent.update_fields()

        raffle_message_id = DB().get_raffle_message_id(guild_id)
        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent)

        await interaction.followup.send(
            f"Raffle entered! Entry Tickets: {tickets}", ephemeral=True
        )

    async def end_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )
            return

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message("This raffle is no longer active!")
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        self.enter_raffle_button.disabled = True
        self.end_raffle_button.disabled = True
        self.redo_raffle_button.disabled = False

        end_time = datetime.now()
        self.parent.end_time = int(end_time.timestamp())
        self.parent.update_fields()

        raffle_message = await interaction.channel.fetch_message(raffle_message_id)
        await raffle_message.edit(embed=self.parent, view=self)

        await RaffleController._end_raffle_impl(
            interaction, raffle_message_id, self.num_winners
        )
        DB().close_raffle(interaction.guild.id, end_time)

    async def redo_raffle_onclick(self, interaction: Interaction):
        if not self.has_role("Mod", interaction):
            await interaction.response.send_message(
                "You must be a mod to do that!", ephemeral=True
            )
            return

        modal = RedoRaffleModal(raffle_message=interaction.message)
        await interaction.response.send_modal(modal)
