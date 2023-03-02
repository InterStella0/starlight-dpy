from typing import List, Union, TypeVar, Iterator

import discord
from discord import app_commands
__all__ = (
    'get_app_signature',
    'recursive_unpack',
    'flatten'
)


T = TypeVar('T')


def recursive_unpack(iterable: List[Union[List[T], T]], /, *, allowed_recursion=(list, tuple, set, dict)) -> Iterator[T]:
    """Used to unpack an iterable from any level of data structure.
    This is similar to :meth:`itertools.chain.from_iterable` but recursive with any level of depth.

    Parameters
    -----------
        iterable: List[Union[List[T], T]]
            The multi level list that will be unpacked.
        allowed_recursion: Tuple[Type]
            Data structure that is allowed to be recursived. Defaults to Tuple[list, tuple, set, dict].

    Yields
    -------
    T
        The element that was uncover from the data structure.
    """
    for e in iterable:
        if isinstance(e, allowed_recursion):
            yield from recursive_unpack(e, allowed_recursion=allowed_recursion)
        else:
            yield e


def flatten(iterable: List[Union[List[T], T]], /, *, allowed_recursion=(list, tuple, set, dict)) -> List[T]:
    """Used to unpack an iterable from any level of list of list into a single list.
    This is similar to :meth:`itertools.chain.from_iterable` but recursive with any level of depth.

    Parameters
    -----------
        iterable: List[Union[List[T], T]]
            The multi level list that will be unpacked.
        allowed_recursion: Tuple[Type]
            Data structure that is allowed to be recursived. Defaults to Tuple[list, tuple, set, dict].

    Returns
    -------
    List[T]
        The list that was uncover from the data stucture.
    """
    return list(recursive_unpack(iterable, allowed_recursion=allowed_recursion))


def get_app_signature(command: app_commands.Command) -> str:
    """To retrieve app command signature similar to :attr:`~discord.ext.commands.Command.signature`.

    Parameters
    -----------
        command: :class:`~discord.app_commands.Command`
            App command to get signature from.

    Returns
    -------
    :class:`str`
        Parameter string that was extracted.
    """

    result = []
    for param in command.parameters:
        name = param.display_name
        if param.type is discord.AppCommandOptionType.attachment:
            # For discord.Attachment we need to signal to the user that it's an attachment
            # It's not exactly pretty but it's enough to differentiate
            if not param.required:
                result.append(f'[{name} (upload a file)]')
            else:
                result.append(f'<{name} (upload a file)>')
            continue

        # for typing.Literal[...], typing.Optional[typing.Literal[...]], and Greedy[typing.Literal[...]], the
        # parameter signature is a literal list of it's values
        if param.choices:
            name = '|'.join(f'"{v.value}"' if isinstance(v.value, str) else v.name for v in param.choices)

        if not param.required:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            if param.default is not discord.utils.MISSING and param.default not in ('', None):
                result.append(f'[{name}={param.default}]')
                continue
            else:
                result.append(f'[{name}]')
        else:
            result.append(f'<{name}>')

    return ' '.join(result)
