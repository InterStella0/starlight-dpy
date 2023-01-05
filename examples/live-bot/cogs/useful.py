import discord
from discord.ext import commands

import starlight
from utils.help_command import MyHelpCommand


class UsefulCog(commands.Cog, name="Useful Category"):
    """Commands that could be useful."""
    def __init__(self, bot):
        self.emoji = "🇺"

        # load help command in useful cog
        GUILD = discord.Object(1010844235857149952)
        help_command = starlight.convert_help_hybrid(MyHelpCommand(), guild=GUILD)  # load the help command.
        bot.help_command = help_command
        help_command.cog = self  # set a category

    @commands.command()
    async def say(self, ctx: commands.Context, *, say: commands.clean_content):
        """Bot say what you say."""
        await ctx.send(say)

    @commands.command(name='say-embed', aliases=['say_embed', 'say_embeds'])
    async def say_embed(self, ctx: commands.Context, *, say: commands.clean_content):
        """Bot say what you say but in an embed."""
        await ctx.send(embed=discord.Embed(title=f"{ctx.author} says", description=say))

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def guild_sync(self, ctx, guild: discord.Guild = commands.parameter(
        default=lambda ctx: ctx.guild, displayed_default="<Current Guild>"
    )):
        """Sync your global slash into a particular guild."""
        tree = ctx.bot.tree
        tree.copy_global_to(guild=guild)
        cmds = await tree.sync(guild=guild)
        await ctx.send(f"Sync `{len(cmds)}` commands.")


async def setup(bot: commands.Bot):
    await bot.add_cog(UsefulCog(bot))
