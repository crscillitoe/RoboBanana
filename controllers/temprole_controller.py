from discord.ext import tasks
import asyncio
import logging
from datetime import datetime, timedelta
import time
from discord import Client, Interaction, Role, User
from pytimeparse.timeparse import timeparse
from functools import partial
from db import DB
from config import Config
from views.pagination.pagination_embed_view import PaginationEmbed, PaginationView

EXPIRATION_CHECK_CADENCE = float(
    Config.CONFIG["TempRoles"]["ExpirationCheckCadenceMinutes"]
)

LOG = logging.getLogger(__name__)


class TempRoleController:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    async def set_role(user: User, role: Role, duration: str, interaction: Interaction):
        user_id = user.id
        delta = timedelta(seconds=timeparse(duration))
        expiration = datetime.now() + delta

        member = interaction.guild.get_member(user_id)
        if member is None:
            return await interaction.response.send_message(
                f"Unable to find provided user - are they in this server?",
                ephemeral=True,
            )

        DB().set_temprole(user_id, role.id, interaction.guild_id, expiration)

        try:
            await member.add_roles(role)
        except:
            temprole = DB().retrieve_temprole(user_id, role.id)
            if temprole is not None:
                DB().delete_temprole(temprole.id)
            return await interaction.response.send_message(
                f"Failed to assign {role.name} to {user.mention}. Ensure this role is"
                " not above RoboBanana.",
                ephemeral=True,
            )

        unixtime = time.mktime(expiration.timetuple())
        await interaction.response.send_message(
            f"Assigned {role.name} to {user.mention} expiring <t:{unixtime:.0f}:f>"
        )

    @staticmethod
    async def extend_role(
        user: User, role: Role, duration: str, interaction: Interaction
    ):
        user_id = user.id
        extension_duration = timedelta(seconds=timeparse(duration))

        member = interaction.guild.get_member(user_id)
        if member is None:
            return await interaction.response.send_message(
                f"Unable to find provided user - are they in this server?",
                ephemeral=True,
            )

        temprole = DB().retrieve_temprole(user_id, role.id)

        expiration = datetime.now()
        # Set temprole if no existing role to extend
        if temprole is None:
            expiration += extension_duration
            DB().set_temprole(user_id, role.id, interaction.guild_id, expiration)
        else:
            expiration = temprole.expiration + extension_duration
            DB().set_temprole(user_id, role.id, interaction.guild_id, expiration)

        unixtime = time.mktime(expiration.timetuple())
        await interaction.response.send_message(
            f"Extended {role.name} for {user.mention}. Now expiring"
            f" <t:{unixtime:.0f}:f>"
        )

    @staticmethod
    async def remove_role(user: User, role: Role, interaction: Interaction):
        temprole = DB().retrieve_temprole(user.id, role.id)
        if temprole is None:
            return await interaction.response.send_message(
                f"No temprole to remove for {user.mention}!", ephemeral=True
            )

        member = interaction.guild.get_member(user.id)
        if member is None:
            return await interaction.response.send_message(
                f"Could not find user {user.mention}!", ephemeral=True
            )

        await member.remove_roles(role)
        DB().delete_temprole(temprole.id)
        await interaction.response.send_message(
            f"Removed {role.name} from {user.mention}"
        )

    @staticmethod
    async def view_temproles(user: User, interaction: Interaction):
        temproles = DB().get_user_temproles(user.id, interaction.guild_id)
        if len(temproles) == 0:
            return await interaction.response.send_message(
                f"{user.mention} does not currently have any temproles assigned!",
                ephemeral=True,
            )

        response = f"{user.mention} current temproles:\n\n"
        for temprole in temproles:
            role = interaction.guild.get_role(temprole.role_id)
            if role is None:
                response += f"Could not find temprole {temprole.role_id}\n"
                continue

            unixtime = time.mktime(temprole.expiration.timetuple())
            response += f"{role.name} expires <t:{unixtime:.0f}:f>\n"

        await interaction.response.send_message(response, ephemeral=True)

    @staticmethod
    async def view_users(role: Role, interaction: Interaction):
        if DB().get_temprole_users_count(role.id, interaction.guild_id) == 0:
            return await interaction.response.send_message(
                f"`@{role.name}` is not currently assigned to any users as a temprole!",
                ephemeral=True,
            )

        page_callback = partial(TempRoleController.get_view_users_page, role, interaction)
        embed = PaginationEmbed(page_callback)
        await embed.get_next_page()
        view = PaginationView(interaction, embed)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @staticmethod
    async def get_view_users_page(
        role: Role, interaction: Interaction, current_page, num_pages, per_page
    ):
        """
        Gets title, description, and num_pages for each page of view_users
        """
        temprole_users_count = DB().get_temprole_users_count(role.id, interaction.guild_id)
        num_pages = (temprole_users_count + per_page - 1) // per_page

        title = f"Users with `@{role.name}` temprole:"
        if num_pages > 1:
            title += f"\t\t(Page {current_page + 1}/{num_pages})\n"

        if current_page + 1 > num_pages:
            description = "There are no longer enough users to fill this page.\n"
            return title, description, num_pages

        description = ""
        offset = current_page * per_page
        for user in DB().get_temprole_users(role.id, interaction.guild_id, offset, limit=per_page):
            member = interaction.guild.get_member(user.user_id)
            if member is None:
                description += f"Could not find user {user.user_id}\n"
            else:
                unixtime = time.mktime(user.expiration.timetuple())
                description += f"{member.mention} expires <t:{unixtime:.0f}:f>\n"

        return title, description, num_pages

    @tasks.loop(minutes=EXPIRATION_CHECK_CADENCE)
    async def expire_roles(self):
        LOG.info("[TEMPROLE TASK] Running expire roles...")
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

            try:
                await member.remove_roles(role)
            except:
                LOG.warn(f"Failed to remove {role} from {member.name}")
                continue
            DB().delete_temprole(expire_role.id)

            # Rate limit
            await asyncio.sleep(1)
