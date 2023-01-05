import copy
import functools
from typing import Any, Dict, Generator, Callable, List, Optional

import discord
from discord.ext import commands
from discord.ext.commands.parameters import Parameter, Signature
from discord.ext.commands.core import get_signature_parameters


__all__ = (
    'convert_help_hybrid',
)

class _InjectorCallback:
    # This class is to ensure that the help command instance gets passed properly
    # The final level of invocation will always leads back to the _original instance
    # hence bind needed to be modified before invoke is called.
    def __init__(self, original_callback, bind):
        self.callback = original_callback
        self.bind = bind

    async def invoke(self, *args, **kwargs):
        # don't put cog in command_callback
        # it used to be that i could do this in parse_arguments, but appcommand extracts __self__ directly from callback
        cog, *args = args
        return await self.callback.__func__(self.bind, *args, **kwargs)


def _method_partial(inject):
    # The reason this is here is
    # method cannot be modified which is required for AppCommand callback
    # Due to the shaky implementation of help command, the callback gets copied several
    # times before getting called.
    try:
        inject.__original_callback__
    except AttributeError:
        inject.__original_callback__ = _InjectorCallback(inject.command_callback, inject)

    invoker = inject.__original_callback__
    original_callback = inject.__original_callback__.callback

    async def invoke(*args, **kwargs):  # allows __signature__ modification
        return await invoker.invoke(*args, **kwargs)

    callback = copy.copy(invoke)
    # retrieve original signature so the user can modify if they want.
    # also good for AppCommand compatibility
    original_signature = Signature.from_callable(original_callback).parameters.values()
    callback.__signature__ = Signature.from_callable(callback).replace(parameters=original_signature)
    inject.command_callback = callback
    return callback


class _HybridHelpCommandImpl(commands.HybridCommand):
    # Most of this is copied from HelpCommandImpl with a bit modification
    def __init__(self, inject: commands.HelpCommand, *args: Any, **kwargs: Any) -> None:
        _method_partial(inject)
        super().__init__(inject.command_callback, *args, **kwargs)
        self._original: commands.HelpCommand = inject
        self._injected: commands.HelpCommand = inject
        self.params: Dict[str, Parameter] = get_signature_parameters(
            inject.__original_callback__.callback, globals(), skip_parameters=1  # type: ignore
        )

    async def prepare(self, ctx: commands.Context) -> None:
        self._injected = injected = self._original.copy()
        injected.context = ctx
        self._original.__original_callback__.bind = injected  # type: ignore
        self.params = get_signature_parameters(
            self._original.__original_callback__.callback, globals(), skip_parameters=1  # type: ignore
        )

        on_error = injected.on_help_command_error
        if not hasattr(on_error, '__help_command_not_overridden__'):
            if self.cog is not None:
                self.on_error = self._on_error_cog_implementation
            else:
                self.on_error = on_error

        await super().prepare(ctx)

    async def _on_error_cog_implementation(self, _, ctx: commands.Context, error: commands.CommandError) -> None:
        await self._injected.on_help_command_error(ctx, error)

    def _inject_into_cog(self, cog: commands.Cog) -> None:
        # Warning: hacky

        # Make the cog think that get_commands returns this command
        # as well if we inject it without modifying __cog_commands__
        # since that's used for the injection and ejection of cogs.
        def wrapped_get_commands(
            *, _original: Callable[[], List[commands.Command[Any, ..., Any]]] = cog.get_commands
        ) -> List[commands.Command[Any, ..., Any]]:
            ret = _original()
            ret.append(self)
            return ret

        # Ditto here
        def wrapped_walk_commands(
            *, _original: Callable[[], Generator[commands.Command[Any, ..., Any], None, None]] = cog.walk_commands
        ):
            yield from _original()
            yield self

        functools.update_wrapper(wrapped_get_commands, cog.get_commands)
        functools.update_wrapper(wrapped_walk_commands, cog.walk_commands)
        cog.get_commands = wrapped_get_commands
        cog.walk_commands = wrapped_walk_commands
        self.cog = cog

    def _eject_cog(self) -> None:
        if self.cog is None:
            return

        # revert back into their original methods
        cog = self.cog
        cog.get_commands = cog.get_commands.__wrapped__
        cog.walk_commands = cog.walk_commands.__wrapped__
        self.cog = None


class _InjectHybridHelpCommand:
    # Properly inject into the important part of the help command
    def __init__(self, help_command: commands.HelpCommand):
        self.help_command = help_command

    def get_destination(self) -> discord.abc.Messageable:
        # better to return context for interaction compatibility.
        return self.help_command.context

    def _add_to_bot(self, bot: commands.bot.BotBase) -> None:
        command = _HybridHelpCommandImpl(self.help_command, **self.help_command.command_attrs)
        self.help_command._command_impl = command
        bot.add_command(command)

    def _remove_from_bot(self, bot: commands.bot.BotBase) -> None:
        bot.remove_command(self.help_command._command_impl.name)
        bot.tree.remove_command(self.help_command._command_impl.app_command.name)
        self.help_command._command_impl._eject_cog()


def convert_help_hybrid(help_command: commands.HelpCommand, **command_attrs: Any) -> commands.HelpCommand:
    """Converts your help command into a hybrid help command.

    This is still experimental feature.

    Parameters
    -----------
        help_command: :class:`~discord.ext.commands.HelpCommand`
            Your help command that will be converted to hybrid.
        **command_attrs: Any
            Attributes that will be assigned to the help command callback. You can set your related app command
            attribute here.

    Returns
    --------
        :class:`~discord.ext.commands.HelpCommand`
            A copy of your help command with hybrid compatibility.
    """
    injected = copy.copy(help_command)
    injected.command_attrs.update(command_attrs)
    command_impl = _HybridHelpCommandImpl(injected, **injected.command_attrs)
    injected._command_impl = command_impl

    injector = _InjectHybridHelpCommand(injected)
    injected.get_destination = injector.get_destination
    injected._add_to_bot = injector._add_to_bot
    injected._remove_from_bot = injector._remove_from_bot
    return injected

