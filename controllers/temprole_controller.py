from discord.ext import tasks
import asyncio
import logging
from datetime import datetime, timedelta
import time
from discord import Client, Interaction, Role
from pytimeparse.timeparse import timeparse
from db import DB
from config import Config

EXPIRATION_CHECK_CADENCE = float(
    Config.CONFIG["TempRoles"]["ExpirationCheckCadenceMinutes"]
)

LOG = logging.getLogger(__name__)


class TempRoleController:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    async def add_temprole(
        user_id: int, role: Role, duration: str, interaction: Interaction
    ):
        delta = timedelta(seconds=timeparse(duration))
        expiration = datetime.now() + delta

        member = interaction.guild.get_member(user_id)
        if member is None:
            return await interaction.response.send_message(
                f"Unable to find provided user - are they in this server?",
                ephemeral=True,
            )

        DB().write_temprole(user_id, role.id, interaction.guild_id, expiration)

        await member.add_roles(role)

        unixtime = time.mktime(expiration.timetuple())
        await interaction.response.send_message(
            f"Assigned temprole expiring <t:{unixtime:.0f}:f>", ephemeral=True
        )

    @staticmethod
    async def view_temproles(interaction: Interaction):
        temproles = DB().get_user_temproles(interaction.user.id, interaction.guild_id)
        if len(temproles) == 0:
            await interaction.response.send_message(
                "You do not currently have any temproles assigned!"
            )

        response = "Your current temproles:\n\n"
        for temprole in temproles:
            role = interaction.guild.get_role(temprole.role_id)
            if role is None:
                response += f"Could not find temprole {temprole.role_id}\n"
                continue

            unixtime = time.mktime(temprole.expiration.timetuple())
            response += f"{role.name} expires <t:{unixtime:.0f}:f>\n"

        await interaction.response.send_message(response, ephemeral=True)

    @tasks.loop(minutes=EXPIRATION_CHECK_CADENCE)
    async def expire_roles(self):
        LOG.debug("Running expire roles...")
        roles_to_expire = DB().get_expired_roles(datetime.now())
        for expire_role in roles_to_expire:
            guild = self.client.get_guild(expire_role.guild_id)
            if guild is None:
                LOG.warn(f"Unable to find {expire_role.guild_id=}")
                continue

            role = guild.get_role(expire_role.role_id)
            if role is None:
                LOG.warn(f"Unable to find {expire_role.role_id=}")
                continue

            member = guild.get_member(expire_role.user_id)
            if member is None:
                LOG.warn(f"Unable to find {expire_role.user_id=}")
                continue

            await member.remove_roles(role)
            DB().delete_temprole(expire_role.id)

            # Rate limit
            await asyncio.sleep(1)
