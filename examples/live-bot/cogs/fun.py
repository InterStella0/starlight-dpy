import random
from typing import Literal

import discord
from discord.ext import commands


class FunCog(commands.Cog, name="Fun Category"):
    """Fun commands for users to use!"""
    def __init__(self):
        self.emoji = "🇫"

    @commands.hybrid_command(name='8ball', aliases=['eight-ball'])
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        """Answers for your question."""
        answers = ['absolutely', 'yes', 'no', 'do not', 'surely', 'clueless']
        embed = discord.Embed(
            description=f"**Asked:**{question}\nMy honest opinion to this information:{random.choice(answers)}",
            color=ctx.bot.accent_color
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='rock-paper-scissor', aliases=['rps'])
    async def rock_paper_scissor(self, ctx: commands.Context, *, item: Literal['rock', 'paper', 'scissor']):
        """Play rock paper scissor."""
        answers = {'rock': 'paper', 'paper': 'scissor', 'scissor': 'rock'}
        choice = random.choice(list(answers))
        response = "I choose '{}'. {}"
        result = "It's a draw."
        if choice != item:
            result = "You win!" if answers[choice] == item else "You lost!"

        await ctx.send(response.format(choice, result))

async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog())
