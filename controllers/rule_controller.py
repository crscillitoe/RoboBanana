from datetime import datetime, timezone
from typing import Optional
from discord import Interaction, Client
import discord
from db import DB
from db.models import PredictionChoice, PredictionEntry, PredictionSummary
from threading import Thread

from views.vod_submissions.vs_background_info_embed import VsBackgroundInfoEmbed
from views.vod_submissions.vs_background_info_view import VsBackgroundInfoView

from views.vod_submissions.vs_general_requirements_embed import VsGeneralRequirementsEmbed
from views.vod_submissions.vs_general_requirements_view import VsGeneralRequirementsView

from views.vod_submissions.vs_party_requirements_embed import VsPartyRequirementsEmbed
from views.vod_submissions.vs_party_requirements_view import VsPartyRequirementsView

from views.vod_submissions.vs_restrictions_embed import VsRestrictionsEmbed
from views.vod_submissions.vs_restrictions_view import VsRestrictionsView

from views.vod_submissions.vs_faq_embed import VsFaqEmbed
from views.vod_submissions.vs_faq_view import VsFaqView



from config import Config
import logging
import requests

PUBLISH_URL = "http://localhost:3000/publish-prediction"
AUTH_TOKEN = Config.CONFIG["Server"]["AuthToken"]

LOG = logging.getLogger(__name__)

VOD_SUBMISSION_RULES_CHANNEL_ID = int(Config.CONFIG["Discord"]["VODSubmissionRulesChannelID"])


class RuleController:
    @staticmethod
    async def post_vod_submission_rules(interaction: Interaction, client: Client
    ):

        generic_view = VsGeneralRequirementsView(
            discord.Embed(color=discord.Colour.yellow(), type='rich'))

        background_info_img = discord.File("images/vod_submission_rules/header.png", filename="header.png")
        background_info_img_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
        background_info_img_embed.set_image(url="attachment://header.png")

        vs_background_info_embed = VsBackgroundInfoEmbed(
            interaction.guild_id)

        requirements_img = discord.File("images/vod_submission_rules/requirements.png", filename="requirements.png")
        requirements_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
        requirements_embed.set_image(url="attachment://requirements.png")

        vs_general_requirements_embed = VsGeneralRequirementsEmbed(
            interaction.guild_id)

        party_img = discord.File("images/vod_submission_rules/party_requirements.png", filename="party_requirements.png")
        party_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
        party_embed.set_image(url="attachment://party_requirements.png")

        vs_party_requirements_embed = VsPartyRequirementsEmbed(
            interaction.guild_id)

        restrictions_img = discord.File("images/vod_submission_rules/restrictions.png", filename="restrictions.png")
        restrictions_img_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
        restrictions_img_embed.set_image(url="attachment://restrictions.png")

        vs_restrictions_embed = VsRestrictionsEmbed(
            interaction.guild_id)

        faq_img = discord.File("images/vod_submission_rules/faq.png", filename="faq.png")
        faq_img_embed = discord.Embed(color=discord.Colour.yellow(), type='rich')
        faq_img_embed.set_image(url="attachment://faq.png")

        vs_faq_embed = VsFaqEmbed(
            interaction.guild_id)

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            file=background_info_img, embed=background_info_img_embed, view=generic_view)
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_background_info_embed, view=generic_view)

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            file=requirements_img, embed=requirements_embed, view=generic_view)
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_general_requirements_embed, view=generic_view)

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            file=party_img, embed=party_embed, view=generic_view)
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_party_requirements_embed, view=generic_view)

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            file=restrictions_img, embed=restrictions_img_embed, view=generic_view)
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_restrictions_embed, view=generic_view)

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            file=faq_img, embed=faq_img_embed, view=generic_view)
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_faq_embed, view=generic_view)

        return

"""
        vs_party_requirements_embed = VsPartyRequirementsEmbed()
        vs_party_requirements_view = VsPartyRequirementsView()

        vs_restrictions_embed = VsRestrictionsEmbed()
        vs_restrictions_view = VsRestrictionsView()

        vs_faq_embed = VsFaqEmbed()
        vs_faq_view = VsFaqView()

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_general_requirements_embed)
        
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_party_requirements_embed, view=vs_party_requirements_view
        )

        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_restrictions_embed, view=vs_restrictions_view
        )
        await client.get_channel(VOD_SUBMISSION_RULES_CHANNEL_ID).send(
            content="", embed=vs_faq_embed, view=vs_faq_view
        )
"""