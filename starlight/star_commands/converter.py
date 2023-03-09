from __future__ import annotations

import functools
import types
import inspect
from typing import Union, Tuple, TypeVar, List, Any, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

__all__ = (
    'Separator',
    'SeparatorTransform',
)

from .errors import ExpectedEndOfSeparatorArgument, BadUnionTransformerArgument

if TYPE_CHECKING:
    from discord.ext.commands.view import StringView

T = TypeVar('T')


async def _actual_conversion(converter_origin: Any, interaction: discord.Interaction, value: str) -> Any:
    try:
        transformer = app_commands.transformers.BUILT_IN_TRANSFORMERS[converter_origin]
    except KeyError:
        if isinstance(converter_origin, app_commands.Transformer):
            return await converter_origin.transform(interaction, value)
    else:
        if isinstance(transformer, app_commands.transformers.IdentityTransformer):
            try:
                converter = commands.converter.CONVERTER_MAPPING[converter_origin]
                ctx = await interaction.client.get_context(interaction)  # type: ignore
                converter = functools.partial(converter().convert, ctx)
            except AttributeError:
                converter = None
            except KeyError:
                converter = converter_origin
                if isinstance(converter_origin, bool):
                    converter = commands.converter._convert_to_bool

            if converter is not None:
                try:
                    return await discord.utils.maybe_coroutine(converter, value)
                except Exception:
                    raise app_commands.TransformerError(value, transformer.type, transformer) from None
        else:
            return await transformer.transform(interaction, value)

    raise TypeError(f"{converter_origin.__name__} must inherit Transformer.")


async def _reduce_converter(converter_origin: Any, interaction: discord.Interaction, value: str) -> Any:
    if getattr(converter_origin, '__origin__', None) is Union:
        errs = []
        for converter in converter_origin.__args__:
            if converter is type(None):  # Do not convert on NoneType encounter.
                return None

            try:
                return await _actual_conversion(converter, interaction, value)
            except app_commands.TransformerError as e:
                errs.append((e.type, e.transformer))

        raise BadUnionTransformerArgument(value, *zip(*errs))

    return await _actual_conversion(converter_origin, interaction, value)


class Separator(app_commands.Transformer):  # Do not subclass Greedy due to greedy transformer.
    r"""A special converter that greedily consumes arguments with a custom delimiter.

    The converter stops consuming arguments once there is no longer a delimiter.
    This converter is supported for application commands as a transformer.

    For example, in the following code:

    .. code-block:: python3

        from starlight import star_commands
        @star_commands.command(bot=bot)
        async def test(ctx, numbers: star_commands.Separator[int], reason: str):
            await ctx.send("numbers: {}, reason: {}".format(numbers, reason))

    An invocation of ``[p]test 1, 2, 3, 4, 5, 6 hello`` would pass ``numbers`` with
    ``[1, 2, 3, 4, 5, 6]`` and ``reason`` with ``hello``\.

    The converter supports custom delimiter as its second argument:

    .. code-block:: python3

        from typing import Literal

        @star_commands.command(bot=bot)
        async def test(ctx, numbers: star_commands.Separator[int, Literal["|"]], reason: str):
            ...

    An invocation of ``[p]test 1 | 2 | 3 | 4 hello`` would pass ``numbers`` with
    ``[1, 2, 3, 4]`` and ``reason`` with ``hello``\.

    .. note::
        This converter requires the usage of :class:`~starlight.star_commands.ExtendedCommand` to function properly due
        to how greedy works in :class:`~discord.ext.commands.Command`.

    Parameters
    ------------
        converter: :class:`Any`
            A class to be used as converter.
        delimiter: :class:`str`
            Must be a string literal with only a single character as your delimiter. Space is not a valid delimiter.
    """

    __slots__ = ('converter', 'delimiter')

    def __init__(self, *, converter: T, delimiter: str = ',') -> None:
        super().__init__()
        self.converter: T = converter
        delimiter = delimiter.strip()
        if len(delimiter) > 1:
            raise RuntimeError(f"Delimiter needs to be a single character. Not {len(delimiter)}.")

        self.delimiter: str = delimiter

    def __repr__(self) -> str:
        converter = getattr(self.converter, '__name__', repr(self.converter))
        return f'Separator[{converter}, {self.delimiter}]'

    def __class_getitem__(cls, params: Union[Tuple[T, str], T]) -> Separator[T]:
        if not isinstance(params, tuple):
            params = params, ','
        if len(params) > 2:
            raise TypeError('Separator[...] only supports up to 2 arguments.')
        converter, delimiter = params

        args = getattr(converter, '__args__', ())
        if discord.utils.PY_310 and converter.__class__ is types.UnionType:  # type: ignore
            converter = Union[args]  # type: ignore

        origin = getattr(converter, '__origin__', None)

        if not (callable(converter) or isinstance(converter, commands.Converter) or origin is not None):
            raise TypeError('Separator[Converter, ...] expects a type or a Converter instance.')

        delimiter = getattr(delimiter, '__args__', (',',))
        if len(delimiter) != 1:
            raise TypeError('Separator[..., Delimiter] expects only a single delimiter.')

        delimiter, = delimiter
        if not isinstance(delimiter, str):
            raise TypeError('Separator[..., Delimiter] expects delimiter to be str.')

        return cls(converter=converter, delimiter=delimiter)

    @property
    def constructed_converter(self) -> Any:
        # Only construct a converter once in order to maintain state between convert calls
        if (
                inspect.isclass(self.converter)
                and (
                (issubclass(self.converter, commands.Converter)
                 and not inspect.ismethod(self.converter.convert))
                or
                (issubclass(self.converter, app_commands.Transformer)
                 and not inspect.ismethod(self.converter.transform))
        )):
            return self.converter()
        return self.converter

    def find_separator(self, view: StringView) -> str:
        # I'm not gonna override StringView and maintain their states. I will just do it in here.
        pos = 0
        while not view.eof:
            current = view.buffer[view.index + pos]
            if current == self.delimiter:
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

    async def transform(self, interaction: discord.Interaction, value: Any, /) -> List[T]:
        view = commands.view.StringView(value)  # type: ignore
        result = []

        is_hybrid_app = isinstance(interaction.command, commands.hybrid.HybridAppCommand)
        converter = self.converter
        ctx = interaction._baton
        parameter = None
        if is_hybrid_app:
            for frameinfo in inspect.stack():
                try:
                    param = frameinfo.frame.f_locals['self']
                    if not isinstance(param, app_commands.transformers.CommandParameter):
                        continue
                except (KeyError, AttributeError):
                    continue
                else:
                    parameter = interaction.command.get_parameter(param.name)
                    if parameter is not None:
                        ctx.current_parameter = parameter
                finally:
                    del frameinfo

        while not view.eof:
            view.skip_ws()
            try:
                argument = self.find_separator(view)
            except IndexError:
                # separator not found
                argument = view.read_rest()
                if not argument:
                    raise ExpectedEndOfSeparatorArgument(self.delimiter, converter) from None

            if is_hybrid_app:
                ctx.current_argument = argument

            if parameter is not None:
                converted = await commands.run_converters(ctx, converter, argument, parameter)
            else:
                # Full compatibility with Slash
                converted = await _reduce_converter(self.converter, interaction, argument)
            result.append(converted)

        return result


class SeparatorTransform(Separator):
    r"""This is :class:`Separator` for application command equivalent of ``Transform[List[str], Separator[str]]``.

    For example, in the following code:

    .. code-block:: python3

        from discord import app_commands
        from starlight import star_commands
        @app_commands.command()
        async def test(ctx, numbers: star_commands.SeparatorTransform[int], reason: str):
            await ctx.send("numbers: {}, reason: {}".format(numbers, reason))

    An invocation of ``/test numbers: 1, 2, 3, 4, 5, 6 reason: hello`` would pass ``numbers`` with
    ``[1, 2, 3, 4, 5, 6]`` and ``reason`` with ``hello``\.
    """
    def __class_getitem__(cls, params: Union[Tuple[T, str], T]) -> SeparatorTransform:
        instance = super().__class_getitem__(params)
        return app_commands.Transform[instance.converter, instance]

