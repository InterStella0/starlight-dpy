from typing import Any, Tuple

import discord
from discord.ext import commands
from discord import app_commands

__all__ = (
    "NotViewOwner",
    "ExpectedEndOfSeparatorArgument",
)
class NotViewOwner(Exception):
    pass


class ExpectedEndOfSeparatorArgument(commands.ArgumentParsingError):
    def __init__(self, separator: str, converter: commands.Converter[Any]) -> None:
        super().__init__(f'Expected an argument after a "{separator}".')
        self.converter: commands.Converter[Any] = converter
        self.separator: str = separator


class BadUnionTransformerArgument(app_commands.AppCommandError):
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
