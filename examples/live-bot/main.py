from __future__ import annotations

import glob
import json

import discord
from discord.ext import commands


class MyBot(commands.Bot):
    """Demonstration bot."""

    def __init__(self):
        super().__init__(command_prefix="uwu ", intents=discord.Intents.all())
        self.accent_color = discord.Color(0xffcccb)
        self.error_color = discord.Color.red()

    async def setup_hook(self) -> None:
        for file in glob.glob('cogs/*.py'):
            cog = file.replace('\\', '.')[:-3]
            await self.load_extension(cog)


bot = MyBot()
with open('config.json') as r:
    config = json.load(r)

bot.run(config["TOKEN"])
