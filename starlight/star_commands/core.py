from __future__ import annotations
from typing import TYPE_CHECKING, Any, Union

from discord.utils import MISSING
from discord.ext import commands

from .converter import Separator
from .errors import ExpectedEndOfSeparatorArgument

if TYPE_CHECKING:
    from discord.ext.commands._types import BotT, ContextT
    from discord.ext.commands.core import _AttachmentIterator
    from discord.ext.commands.hybrid import CommandCallback, CogT, P, T

__all__ = (
    "ExtendedCommand",
    "command",
    "hybrid_command"
)


class ExtendedCommandMixin(commands.Command):
    async def transform(
            self, ctx: commands.Context[BotT], param: commands.Parameter, attachments: _AttachmentIterator, /
    ) -> Any:
        converter = param.converter
        if isinstance(converter, Separator):  # Explicit Separator check
            if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY, param.KEYWORD_ONLY):
                return await self._transform_separator_var(ctx, param, converter.constructed_converter)
            elif param.kind is param.VAR_POSITIONAL:
                return await self._transform_separator_pos_var(ctx, param, converter.constructed_converter)
            else:
                raise RuntimeError("Invalid Separator state. There is no way for this to be raised.")

        return await super().transform(ctx, param, attachments)

    async def _transform_separator_var(self, ctx: commands.Context[BotT], param: commands.Parameter, converter: Any) -> Any:
        view = ctx.view
        result = []
        separator_converter = param.converter
        sep_ended = False
        while not view.eof and not sep_ended:
            view.skip_ws()
            try:
                ctx.current_argument = argument = separator_converter.find_separator(view)
            except IndexError:
                # separator not found
                argument = view.read_rest() if param.kind == param.KEYWORD_ONLY else view.get_quoted_word()
                if not argument:
                    raise ExpectedEndOfSeparatorArgument(separator_converter.delimiter, converter) from None

                ctx.current_argument = argument
                sep_ended = True

            value = await commands.run_converters(ctx, converter, argument, param)  # type: ignore
            result.append(value)

        if not result and not param.required:
            return await param.get_default(ctx)
        return result

    async def _transform_separator_pos_var(self, ctx: commands.Context[BotT], param: commands.Parameter, converter: Any) -> Any:
        view = ctx.view
        previous = view.index
        separator_converter = param.converter
        try:
            ctx.current_argument = argument = separator_converter.find_separator(view)
        except IndexError:
            # separator not found
            argument = view.read_rest()
            if not argument:
                raise ExpectedEndOfSeparatorArgument(separator_converter.delimiter, converter) from None

            ctx.current_argument = argument

        try:
            value = await commands.run_converters(ctx, converter, argument, param)  # type: ignore
        except (commands.CommandError, commands.ArgumentParsingError):
            view.index = previous
            raise RuntimeError() from None  # break loop
        else:
            return value


class ExtendedCommand(ExtendedCommandMixin):
    pass


class ExtendedHybridCommand(ExtendedCommandMixin, commands.HybridCommand):
    pass


def command(*args, bot: Union[commands.Bot, MISSING] = MISSING, **kwargs) -> Any:
    """Extended command decorator to create a new command.

    .. code-block:: python3

        from starlight import star_commands

        @star_commands.command(bot=bot)
        async def my_command(ctx: commands.Context):
            await ctx.send('hello')

    .. code-block:: python3

        from starlight import star_commands

        class MyCog(commands.Cog):
            @star_commands.command()
            async def my_command(self, ctx: commands.Context):
                await ctx.send('hello')

    Parameters
    ------------
    bot: :class:`~discord.ext.commands.Bot`
        Optional keyword only parameter to your bot.
    """
    if bot is not MISSING:
        return bot.command(*args, cls=ExtendedCommand, **kwargs)
    return commands.command(*args, cls=ExtendedCommand, **kwargs)


def hybrid_command(*args, bot: Union[commands.Bot, MISSING] = MISSING, **kwargs):
    """Extended hybrid command decorator to create a new command.

    .. code-block:: python3

        from starlight import star_commands

        @star_commands.hybrid_command(bot=bot)
        async def my_command(ctx: commands.Context):
            await ctx.send('hello')

    .. code-block:: python3

        from starlight import star_commands

        class MyCog(commands.Cog):
            @star_commands.hybrid_command()
            async def my_command(self, ctx: commands.Context):
                await ctx.send('hello')

    Parameters
    ------------
    bot: :class:`~discord.ext.commands.Bot`
        Optional keyword only parameter to your bot.
    """
    def decorator(func: CommandCallback[CogT, ContextT, P, T]) -> ExtendedHybridCommand[CogT, P, T]:
        if isinstance(func, commands.Command):
            raise TypeError('Callback is already a command.')

        if bot is not MISSING:
            kwargs.setdefault('parent', bot)
            cmd = ExtendedHybridCommand(func, *args, **kwargs)
            bot.add_command(cmd)
        else:
            cmd = ExtendedHybridCommand(func, *args, **kwargs)
        return cmd
    return decorator
