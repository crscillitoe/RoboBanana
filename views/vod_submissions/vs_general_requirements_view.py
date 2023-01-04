from discord.ui import View
from .vs_general_requirements_embed import VsGeneralRequirementsEmbed

class VsGeneralRequirementsView(View):
    def __init__(
        self, parent: VsGeneralRequirementsEmbed
    ) -> None:
        super().__init__(timeout=None)

        self.parent = parent
        
