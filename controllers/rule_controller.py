import json

from discord import Interaction, Client
import discord

from views.vod_submissions.vs_generic_embed import VsGenericEmbed
from views.vod_submissions.vs_generic_view import VsGenericView

from config import Config
import logging

LOG = logging.getLogger(__name__)

VOD_SUBMISSION_RULES_CHANNEL_ID = int(Config.CONFIG["Discord"]["VODSubmissionRulesChannelID"])

rule_sections = ["background_info", "requirements", "party_requirements", "restrictions", "faq"]

class RuleController:
    @staticmethod
    async def post_vod_submission_rules(interaction: Interaction, client: Client
    ):
        generic_view = VsGenericView(
            discord.Embed(color=discord.Colour.yellow(), type='rich'))

        for rule_section in rule_sections:
            with open('./files/vod_submission/vs_{}.json'.format(rule_section), 'r') as f:
                section_json = json.load(f)
            embed_img_file = discord.File("images/vod_submission_rules/{}.png".format(rule_section), filename="{}.png".format(rule_section))
            img_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
            img_embed.set_image(url="attachment://{}.png".format(rule_section))

            rule_section_embed = VsGenericEmbed(
                interaction.guild_id, section_json)

            await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
                file=embed_img_file, embed=img_embed, view=generic_view)
            await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
                embed=rule_section_embed, view=generic_view)

        return