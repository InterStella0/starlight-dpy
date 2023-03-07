from __future__ import annotations
from typing import Union, Tuple, TypeVar

from discord.ext import commands

__all__ = (
    'Separator',
)

T = TypeVar('T')
class Separator(commands.Greedy):
    def __init__(self, *, converter: T, separator: str = ','):
        super().__init__(converter=converter)
        if len(separator) > 1:
            raise RuntimeError(f"Separator need to be a single character. Not {len(separator)}.")

        self.separator = separator

    def __repr__(self) -> str:
        return self.replace_type(super().__repr__())

    @staticmethod
    def replace_type(original_type: str) -> str:
        _type = original_type.lstrip('Greedy')
        return f'Separator{_type}'

    def __class_getitem__(cls, params: Union[Tuple[T], T]) -> Separator[T]:
        try:
            return super().__class_getitem__(params)
        except TypeError as e:
            message = str(e)
            if message.endswith('[str] is invalid.'):
                return cls(converter=str)  # params is for sure str
            raise TypeError(cls.replace_type(message))
