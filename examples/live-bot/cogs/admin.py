from typing import Union, Annotated, Optional

import discord.utils
import starlight
from discord.ext import commands
from starlight import star_commands

from utils.pagination import StellaPagination


class AdminCog(commands.Cog, name="Admin Category"):
    """Server administration related commands."""

    def __init__(self):
        self.emoji = "🇦"

    @commands.command(name='list-ban', aliases=['list_ban', 'list_bans', 'list-bans'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def list_ban(self, ctx: commands.Context):
        """List all of the banned users."""

        banned_users = [user async for user in ctx.guild.bans()]
        if not banned_users:
            raise commands.BadArgument("No banned user in this server.")

        per_page = 5
        chunks = discord.utils.as_chunks(banned_users, per_page)
        view = StellaPagination(chunks, cache_page=True)
        async for item in starlight.inline_pagination(view, ctx):
            embed = discord.Embed(title=f"Banned Users ({view.current_page + 1}/{view.max_pages})")
            generator = enumerate(item.data, start=view.current_page * per_page + 1)
            lists = ['{0}.{1.user}\n{1.reason}'.format(i, u) for i, u in generator]
            embed.description = "\n".join(lists)
            embed.colour = ctx.bot.accent_color
            item.format(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def bans(self, ctx: commands.Context, *users: Union[discord.Member, discord.User]):
        """Ban multiple users stated by the moderator."""

        for u in users:
            await ctx.guild.ban(u, reason='no reason')

        await ctx.send(f'Banned {", ".join(map(str, users))}')

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def unbans(self, ctx: commands.Context, *users: discord.User):
        """Unbanning multiple users stated by the moderator."""

        for u in users:
            await ctx.guild.unban(u, reason='no reason')

        await ctx.send(f'Unbanned {", ".join(map(str, users))}')

    @star_commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def warn_users(self, ctx: commands.Context,
                         users: star_commands.Separator[Union[discord.Member, discord.User]],
                         *, reason: Annotated[Optional[str], str.strip] = None):
        all_users = ", ".join(map(str, users))
        formatted = '{} has been warned with reason: "{}"' if reason else '{} has been warned.'
        await ctx.send(formatted.format(all_users, reason))




async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog())
