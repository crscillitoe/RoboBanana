from discord.ext import tasks
import asyncio
import logging
from datetime import datetime, timedelta
import time
from discord import Client, Interaction, Role, User, utils
from pytimeparse.timeparse import timeparse
from functools import partial
from db import DB
from config import YAMLConfig as Config
from util.discord_utils import DiscordUtils
from views.pagination.pagination_embed_view import PaginationEmbed, PaginationView

EXPIRATION_CHECK_CADENCE = Config.CONFIG["Discord"]["TempRoles"][
    "ExpirationCheckCadenceMinutes"
]
# this is hardcoded until raze to radiant is over, or config file changes are allowed
# TOP_ROLE_ACCEPTED should be 1077265826886979634 when committing and refers to the ▬▬▬▬▬Subscriptions▬▬▬▬▬ role
TOP_ROLE_ACCEPTED = 1077265826886979634

LOG = logging.getLogger(__name__)


class TempRoleController:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    async def set_role(user: User | int, role: Role, duration: str) -> tuple[bool, str]:
        if hasattr(user, "id"):
            user_id = user.id
        else:
            user_id = user

        try:
            delta = timedelta(seconds=timeparse(duration))
            expiration = datetime.now() + delta
        except:
            return (
                False,
                "Unable to assign role - please provide a time indicator for duration (e.g. s for seconds, m for minutes)",
            )
        guild = role.guild

        member = guild.get_member(user_id)
        if member is None:
            return (
                False,
                "Unable to find provided user - are they in this server?",
            )

        DB().set_temprole(user_id, role.id, guild.id, expiration)

        try:
            await member.add_roles(role)
        except:
            temprole = DB().retrieve_temprole(user_id, role.id)
            if temprole is not None:
                DB().delete_temprole(temprole.id)
                return (
                    False,
                    (
                        f"Failed to assign {role.name} to {member.mention}. Ensure this"
                        " role is not above RoboBanana."
                    ),
                )

        unixtime = time.mktime(expiration.timetuple())
        return (
            True,
            f"Assigned {role.mention} to {member.mention} expiring <t:{unixtime:.0f}:f>",
        )

    @staticmethod
    async def extend_role(user: User, role: Role, duration: str):
        user_id = user.id

        try:
            extension_duration = timedelta(seconds=timeparse(duration))
        except:
            return (
                False,
                "Unable to extend role - please provide a time indicator for duration (e.g. s for seconds, m for minutes)",
            )

        guild = role.guild

        member = guild.get_member(user_id)
        if member is None:
            return (
                False,
                "Unable to find provided user - are they in this server?",
            )

        temprole = DB().retrieve_temprole(user_id, role.id)

        expiration = datetime.now()
        # Set temprole if no existing role to extend
        if temprole is None:
            expiration += extension_duration
            DB().set_temprole(user_id, role.id, guild.id, expiration)
            # Add role to user
            try:
                await member.add_roles(role)
            except:
                temprole = DB().retrieve_temprole(user_id, role.id)
                if temprole is not None:
                    DB().delete_temprole(temprole.id)
                return (
                    False,
                    (
                        f"Failed to assign {role.name} to {user.mention}. Ensure this"
                        " role is not above RoboBanana."
                    ),
                )
        else:
            expiration = temprole.expiration + extension_duration
            DB().set_temprole(user_id, role.id, guild.id, expiration)

        unixtime = time.mktime(expiration.timetuple())
        return (
            True,
            (
                f"Extended {role.mention} for {user.mention}. Now expiring"
                f" <t:{unixtime:.0f}:f>"
            ),
        )

    @staticmethod
    def user_has_temprole(user: User, role: Role):
        temprole = DB().retrieve_temprole(user.id, role.id)
        return temprole is not None

    @staticmethod
    async def remove_role(user: User, role: Role):
        guild = role.guild
        temprole = DB().retrieve_temprole(user.id, role.id)
        if temprole is None:
            return False, f"No temprole to remove for {user.mention}!"

        member = guild.get_member(user.id)
        if member is None:
            return False, f"Could not find user {user.mention}!"

        await member.remove_roles(role)
        DB().delete_temprole(temprole.id)
        return True, f"Removed {role.mention} from {user.mention}."

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

        page_callback = partial(
            TempRoleController.get_view_users_page, role, interaction
        )
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
        temprole_users_count = DB().get_temprole_users_count(
            role.id, interaction.guild_id
        )
        num_pages = (temprole_users_count + per_page - 1) // per_page

        title = f"Users with `@{role.name}` temprole:"
        if num_pages > 1:
            title += f"\t\t(Page {current_page + 1}/{num_pages})\n"

        if current_page + 1 > num_pages:
            description = "There are no longer enough users to fill this page.\n"
            return title, description, num_pages

        description = ""
        offset = current_page * per_page
        for user in DB().get_temprole_users(
            role.id, interaction.guild_id, offset, limit=per_page
        ):
            member = interaction.guild.get_member(user.user_id)
            if member is None:
                description += f"Could not find user {user.user_id}\n"
            else:
                unixtime = time.mktime(user.expiration.timetuple())
                description += f"{member.mention} expires <t:{unixtime:.0f}:f>\n"

        return title, description, num_pages

    @staticmethod
    async def authorise_role_usage(role: Role):
        """
        Checks whether role is allowed to be used based on top role accepted (does not include top role)
        """
        guild = role.guild

        top_role_accepted = guild.get_role(TOP_ROLE_ACCEPTED)
        if top_role_accepted is None:
            return False, f"Top accepted role could not be initialised"

        if top_role_accepted > role:
            return True, f"{role} can be used"
        else:
            return False, f"{role} is higher than the top role accepted"

    @tasks.loop(minutes=EXPIRATION_CHECK_CADENCE)
    async def expire_roles(self):
        LOG.info("[TEMPROLE TASK] Running expire roles...")
        roles_to_expire = DB().get_expired_roles(datetime.now())
        for expire_role in roles_to_expire:
            guild = self.client.get_guild(expire_role.guild_id)
            if guild is None:
                LOG.warn(f"Unable to find {expire_role.guild_id=}")
                DB().delete_temprole(expire_role.id)
                continue

            role = guild.get_role(expire_role.role_id)
            if role is None:
                LOG.warn(f"Unable to find {expire_role.role_id=}")
                DB().delete_temprole(expire_role.id)
                continue

            member = guild.get_member(expire_role.user_id)
            if member is None:
                LOG.warn(f"Unable to find {expire_role.user_id=}")
                DB().delete_temprole(expire_role.id)
                continue

            try:
                await member.remove_roles(role)
            except:
                LOG.warn(f"Failed to remove {role} from {member.name}")
                continue
            DB().delete_temprole(expire_role.id)

            # Rate limit
            await asyncio.sleep(1)
