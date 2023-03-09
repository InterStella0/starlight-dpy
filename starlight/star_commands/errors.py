from typing import Any, Tuple

import discord
from discord.ext import commands
from discord import app_commands

__all__ = (
    "NotViewOwner",
    "ExpectedEndOfSeparatorArgument",
    "BadUnionTransformerArgument",
)
class NotViewOwner(Exception):
    """Raised within a view invocation where the view is not the owner of a View."""


class ExpectedEndOfSeparatorArgument(commands.ArgumentParsingError):
    """Raised only when a separator ends unexpectedly. For example, ``[p]test 1, 2,`` is invalid.

    Attributes
    ------------
        converter: :class:`Any`
            Converter that were involved with the separator.
        delimiter: :class:`str`
            The delimiter associated with the separator.
    """
    def __init__(self, delimiter: str, converter: commands.Converter[Any]) -> None:
        super().__init__(f'Expected an argument after a "{delimiter}".')
        self.converter: commands.Converter[Any] = converter
        self.delimiter: str = delimiter


class BadUnionTransformerArgument(app_commands.AppCommandError):
    """Raised only when a separator ends unexpectedly. For example, ``[p]test 1, 2,`` is invalid.

    Attributes
    ------------
        value: :class:`Any`
            The value that were attempted to be converted.
        types: Tuple[:class:`~discord.AppCommandOptionType`]
            Option types regarding the converter.
        transformers: Tuple[:class:`~discord.app_commands.Transformer`]
            Transformers that were involved trying to convert the value.
    """

    def __init__(self, value: Any, opt_types: Tuple[discord.AppCommandOptionType], transformers: Tuple[app_commands.Transformer]) -> None:
        self.value: Any = value
        self.types: Tuple[discord.AppCommandOptionType] = opt_types
        self.transformers: Tuple[app_commands.Transformer] = transformers

        to_string = [f'{transformer._error_display_name!s}'
                     if not isinstance(transformer, app_commands.transformers.IdentityTransformer)
                     else str(transformer.type).rpartition('.')[-1]
                     for transformer in transformers]

        if len(to_string) > 2:
            fmt = '{}, or {}'.format(', '.join(to_string[:-1]), to_string[-1])
        else:
            fmt = ' or '.join(to_string)

        super().__init__(f'Failed to convert {value} to {fmt}')
