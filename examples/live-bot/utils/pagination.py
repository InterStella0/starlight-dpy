import discord
import starlight


class StellaPagination(starlight.SimplePaginationView):
    @discord.ui.button(emoji='<:backward:1059315483599446156>')
    async def start_button(self, interaction, button):
        await self.to_start(interaction)

    @discord.ui.button(emoji='<:left:1059315476737572904>')
    async def previous_button(self, interaction, button):
        await self.to_previous(interaction)

    @discord.ui.button(emoji='<:stop:1059315479979774072>')
    async def stop_button(self, interaction, button):
        await self.to_stop(interaction)

    @discord.ui.button(emoji='<:right:1059315473369538570>')
    async def next_button(self, interaction, button):
        await self.to_next(interaction)

    @discord.ui.button(emoji='<:forward:1059315487017808014>')
    async def end_button(self, interaction, button):
        await self.to_end(interaction)
