import glob

import discord
from discord.ext import commands


class MyBot(commands.Bot):
    """Demonstration bot."""

    def __init__(self):
        super().__init__(command_prefix="??", intents=discord.Intents.all())
        self.accent_color = discord.Color(0xffcccb)
        self.error_color = discord.Color.red()

    async def setup_hook(self) -> None:
        for file in glob.glob('cogs/*.py'):
            cog = file.replace('\\', '.')[:-3]
            await self.load_extension(cog)


bot = MyBot()
token = ""
bot.run(token)
