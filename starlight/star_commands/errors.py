from typing import Any

from discord.ext import commands

__all__ = (
    "NotViewOwner",
    "ExpectedEndOfSeparatorArgument",
)
class NotViewOwner(Exception):
    pass


class ExpectedEndOfSeparatorArgument(commands.ArgumentParsingError):
    def __init__(self, separator: str, converter: commands.Converter[Any]):
        super().__init__(f'Expected an argument after a "{separator}".')
        self.converter: commands.Converter[Any] = converter
        self.separator: str = separator
