from __future__ import annotations
from typing import TYPE_CHECKING, Any

from discord.ext import commands

from .converter import Separator
from .errors import ExpectedEndOfSeparatorArgument

if TYPE_CHECKING:
    from discord.ext.commands.view import StringView
    from discord.ext.commands._types import BotT
    from discord.ext.commands.core import _AttachmentIterator

__all__ = (
    "ExtendedCommand",
    "command",
)

class ExtendedCommand(commands.Command):
    async def transform(
            self, ctx: commands.Context[BotT], param: commands.Parameter, attachments: _AttachmentIterator, /
    ) -> Any:
        converter = param.converter
        if type(converter) is Separator:  # Explicit Separator check
            if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY, param.KEYWORD_ONLY):
                return await self._transform_separator_var(ctx, param, converter.constructed_converter)
            elif param.kind is param.VAR_POSITIONAL:
                return await self._transform_separator_pos_var(ctx, param, converter.constructed_converter)
            else:
                raise RuntimeError("Invalid Separator state.")

        return await super().transform(ctx, param, attachments)

    async def _transform_separator_var(self, ctx: commands.Context[BotT], param: commands.Parameter, converter: Any) -> Any:
        view = ctx.view
        result = []
        sep = param.converter.separator
        sep_ended = False
        while not view.eof and not sep_ended:
            view.skip_ws()
            try:
                ctx.current_argument = argument = self._find_separator(view, sep)
            except IndexError:
                # separator not found
                argument = view.read_rest() if param.kind == param.KEYWORD_ONLY else view.get_quoted_word()
                if not argument:
                    raise ExpectedEndOfSeparatorArgument(sep, converter) from None
                sep_ended = True

            value = await commands.run_converters(ctx, converter, argument, param)  # type: ignore
            result.append(value)

        if not result and not param.required:
            return await param.get_default(ctx)
        return result

    async def _transform_separator_pos_var(self, ctx: commands.Context[BotT], param: commands.Parameter, converter: Any) -> Any:
        view = ctx.view
        previous = view.index
        sep = param.converter.separator
        try:
            ctx.current_argument = argument = self._find_separator(view, sep)
        except IndexError:
            # separator not found
            argument = view.read_rest()
            if not argument:
                raise ExpectedEndOfSeparatorArgument(sep, converter) from None

        try:
            value = await commands.run_converters(ctx, converter, argument, param)  # type: ignore
        except (commands.CommandError, commands.ArgumentParsingError):
            view.index = previous
            raise RuntimeError() from None  # break loop
        else:
            return value

    def _find_separator(self, view: StringView, target: str) -> str:
        # I'm not gonna override StringView and maintain their states. I will just do it in here.
        pos = 0
        while not view.eof:
            current = view.buffer[view.index + pos]
            if current == target:
                break
            pos += 1
        else:
            raise IndexError("Not Found")

        sep_pos = pos
        view.previous = view.index
        while pos > 1:  # ignore after whitespace
            pos -= 1
            current = view.buffer[view.index + pos]
            if current.isspace():
                continue
            else:
                pos += 1
                break

        result = view.buffer[view.index: view.index + pos]
        view.index += sep_pos + 1  # step over the separator. Explicit sep should only be 1 char length.
        if view.eof:
            raise IndexError("Malformed Separator.")

        return result


def command(*args, **kwargs) -> Any:
    return commands.command(*args, cls=ExtendedCommand, **kwargs)

