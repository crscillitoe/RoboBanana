from discord import Embed, ButtonStyle
from discord.ui import View, button


class PaginationEmbed(Embed):
    """
    Calls page_callback to get the next page for PaginationView

    Args:
        page_callback (callable): Callback that gets the title, desc, and updated number of pages
            Called with additional parameters: current_page (int), num_pages (int), per_page (int)
            Returns: title (str), description (str), num_pages (int)
        per_page (int): Number of results per page. Passed to page_callback
    """

    def __init__(self, page_callback, per_page=10):
        super().__init__()
        self.page_callback = page_callback
        self.per_page = per_page
        self.current_page = 0
        self.num_pages = None

    async def get_next_page(self):
        self.title, self.description, self.num_pages = await self.page_callback(
            self.current_page, self.num_pages, self.per_page
        )
        return self


class PaginationView(View):
    def __init__(self, interaction, pagination_embed):
        super().__init__()
        self.interaction = interaction
        self.embed = pagination_embed
        self.next_button.disabled = self.embed.num_pages == 1

    @button(label="Previous", style=ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        if self.embed.current_page > 0:
            self.embed.current_page -= 1
            await self.update_embed()

    @button(label="Next", style=ButtonStyle.secondary)
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        if self.embed.current_page < self.embed.num_pages - 1:
            self.embed.current_page += 1
            await self.update_embed()

    async def update_embed(self):
        embed = await self.embed.get_next_page()
        message = await self.interaction.original_response()
        self.prev_button.disabled = self.embed.current_page == 0
        self.next_button.disabled = self.embed.current_page >= self.embed.num_pages - 1
        await message.edit(embed=embed, view=self)

    async def on_timeout(self):
        self.next_button.disabled = True
        self.prev_button.disabled = True
        message = await self.interaction.original_response()
        await message.edit(embed=self.embed, view=self)
        self.stop()
