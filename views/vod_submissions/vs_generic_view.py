from discord.ui import View
from .vs_generic_embed import VsGenericEmbed

class VsGenericView(View):
    def __init__(
        self, parent: VsGenericEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        
