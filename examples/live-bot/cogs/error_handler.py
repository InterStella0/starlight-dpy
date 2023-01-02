from discord.ext import commands


class ErrorHandler(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)   # cie unwrapped
        ignore = (commands.CommandNotFound,)
        if isinstance(error, ignore):
            return

        await ctx.send(str(error))
        raise error


async def setup(bot):
    await bot.add_cog(ErrorHandler())
