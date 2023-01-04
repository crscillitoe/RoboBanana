from discord.ui import View
from .vs_faq_embed import VsFaqEmbed

class VsFaqView(View):
    def __init__(
        self, parent: VsFaqEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        
