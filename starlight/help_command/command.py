from __future__ import annotations

from typing import Optional, List, Any, Union, Dict, TypeVar, Mapping, Type

import discord
from discord.ext import commands

from .view import HelpMenuCommand, HelpMenuProvider, HelpMenuGroup, HelpMenuError, HelpMenuCog, MenuHomeButton
from ..views.pagination import ViewAuthor

__all__ = (
    "MenuHelpCommand",
)

T = TypeVar('T')
_Command = commands.Command[Any, ..., Any]
_MappingBotCommands = Dict[Optional[commands.Cog], List[_Command]]
_OptionalFormatReturns = Union[discord.Embed, Dict[str, Any], str]


class MenuHelpCommand(commands.HelpCommand):
    """HelpCommand implementation for MenuHelpCommand which
       utilizes discord.ui.Select for Cog selection and discord.ui.Button for
       command pagination. This subclass the HelpCommand.

    Attributes
    ------------
    per_page: int
        Amount of items per page that are displayed. This applies to Cog menu and command pagination. Defaults to 6.
    sort_commands: :class:`bool`
        Sort commands in ascending order based on the command name. Default to True.
    no_documentation: :class:`str`
        Text displayed when a command does not have a command description. Defaults to 'No Documentation'.
    no_category: :class:`str`
        Text display for commands that does not have a Cog associated with it. Defaults to 'No Category'
    accent_color: :class:`str`
        Color of embed for normal display. Defaults to `discord.Color.blurple`.
    error_color: Union[discord.Color, :class: `int`]
        Color of embed for error display. Defaults to `discord.Color.red`.
    pagination_buttons: Optional[Mapping[ :class: `str`, discord.ui.Button]]
        Mapping of pagination discord.ui.Button instances for each pagination iteraction.
    cls_home_button: Type[MenuHomeButton]
        discord.ui.Button class for the home button.
    view_provider: HelpMenuProvider
        An instance that provides View for each command use cases. Best way to give custom a discord.ui.View onto the
        MenuHelpCommand.
    original_message: Optional[Message]
        A Message instance that was initially sent by the MenuHelpCommand.
    """

    def __init__(self, *,
                 per_page: int = 6,
                 sort_commands: bool = True,
                 no_documentation: str = "No Documentation",
                 no_category: str = "No Category",
                 accent_color: Union[discord.Color, int] = discord.Color.blurple(),
                 error_color: Union[discord.Color, int] = discord.Color.red(),
                 pagination_buttons: Optional[Mapping[str, discord.ui.Button]] = None,
                 cls_home_button: Type[MenuHomeButton] = MenuHomeButton,
                 **options):
        super().__init__(**options)
        self.no_category: str = no_category
        self.per_page: int = per_page
        self.accent_color: Union[discord.Color, int] = accent_color
        self.error_color: Union[discord.Color, int] = error_color
        self.no_documentation: str = no_documentation
        self.sort_commands: bool = sort_commands
        self.view_provider: HelpMenuProvider = HelpMenuProvider(self)
        self.original_message: Optional[discord.Message] = None
        self.pagination_buttons = pagination_buttons
        self.cls_home_button = cls_home_button

    @property
    def pagination_buttons(self) -> Mapping[str, discord.ui.Button]:
        return self._pagination_buttons or {
            "start_button": discord.ui.Button(emoji="⏪"),
            "previous_button": discord.ui.Button(emoji="◀️"),
            "stop_button": discord.ui.Button(emoji="⏹️"),
            "next_button": discord.ui.Button(emoji="▶️"),
            "end_button": discord.ui.Button(emoji="⏩")
        }

    @pagination_buttons.setter
    def pagination_buttons(self, value: Mapping[str, discord.ui.Button]):
        self._pagination_buttons = value

    def get_command_signature(self, command: _Command, /) -> str:
        """Retrieves the Command signature during Command pagination.

        Parameters
        ------------
        command: :class:`Command`
            The command to get the signature of.
        Returns
        --------
        :class:`str`
            The signature for the command.
        """
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'

    def format_command_brief(self, cmd: _Command) -> str:
        """Retrieves the Command signature with a brief description during Command pagination.

        Parameters
        ------------
        command: :class:`Command`
            The command to get the signature of.
        Returns
        --------
        :class:`str`
            The signature for the command.
        """
        return f"{self.get_command_signature(cmd)}\n{cmd.short_doc or self.no_documentation}"

    async def format_group_detail(self, view: HelpMenuGroup) -> _OptionalFormatReturns:
        """Interface to display a detail description of a Group command.

        Parameters
        ------------
        view: HelpMenuGroup
            The view that is associated with the Message.
        Returns
        --------
        :class: Union[discord.Embed, Dict[`str`, Any], `str`]
            The value to be display on the Message.
        """
        group = view.group
        subcommands = "\n".join([self.format_command_brief(cmd) for cmd in group.commands])
        group_description = group.help or self.no_documentation
        description = group_description + f"\n\n**Subcommands**\n{subcommands}" if subcommands else ""
        return discord.Embed(
            title=self.get_command_signature(group),
            description=description,
            color=self.accent_color
        )

    async def format_command_detail(self, view: HelpMenuCommand) -> _OptionalFormatReturns:
        """Interface to display a detail description of a Command.

        Parameters
        ------------
        view: HelpMenuCommand
            The view that is associated with the Message.
        Returns
        --------
        :class: Union[discord.Embed, Dict[`str`, Any], `str`]
            The value to be display on the Message.
        """
        cmd = view.command
        return discord.Embed(
            title=self.get_command_signature(cmd),
            description=cmd.help,
            color=self.accent_color
        )

    async def format_error_detail(self, view: HelpMenuError) -> _OptionalFormatReturns:
        """Interface to display a detail description of an error that occurred.

        Parameters
        ------------
        view: HelpMenuError
            The view that is associated with the error Message.
        Returns
        --------
        :class: Union[discord.Embed, Dict[`str`, Any], `str`]
            The value to be display on the Message.
        """
        return discord.Embed(
            title="Something went wrong!",
            description=str(view.error),
            color=self.error_color
        )

    def resolve_cog_name(self, cog: Optional[commands.Cog]) -> str:
        """Resolves the cog name of a given Cog instance.

        Parameters
        ------------
        cog: Optional[commands.Cog]
            The cog to resolve the name.
        Returns
        --------
        :class: `str`
            The name of the cog.
        """
        return getattr(cog, "qualified_name", None) or self.no_category

    async def __normalized_kwargs(self, callback, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        formed_interface = await discord.utils.maybe_coroutine(callback, *args, **kwargs)
        if isinstance(formed_interface, dict):
            return formed_interface
        elif isinstance(formed_interface, discord.Embed):
            return {"embed": formed_interface}
        return {"content": formed_interface}

    async def form_front_bot_menu_kwargs(self, mapping: _MappingBotCommands) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto Message.edit key arguments.
        Mostly used to resolve key arguments from `MenuHelpCommand.form_front_bot_menu`.

        Parameters
        ------------
        mapping: Dict[Optional[commands.Cog], List[Command]]
            The dictionary that is mapped on Cog and the list Command associated with it.
        Returns
        --------
        :class: Dict[str, Any]
            The keyword arguments to be given onto the `Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_front_bot_menu, mapping)

    async def form_command_detail_kwargs(self, view: HelpMenuCommand) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto Message.edit key arguments.
        Mostly used to resolve key arguments from `MenuHelpCommand.format_command_detail`.

        Parameters
        ------------
        view: HelpMenuCommand
            The discord.ui.View associated with the command detail.
        Returns
        --------
        :class: Dict[str, Any]
            The keyword arguments to be given onto the `Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_command_detail, view)

    async def form_group_detail_kwargs(self, view: HelpMenuGroup) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto Message.edit key arguments.
        Mostly used to resolve key arguments from `MenuHelpCommand.format_group_detail`.

        Parameters
        ------------
        view: HelpMenuGroup
            The discord.ui.View associated with the group detail.
        Returns
        --------
        :class: Dict[str, Any]
            The keyword arguments to be given onto the `Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_group_detail, view)

    async def form_error_detail_kwargs(self, view: HelpMenuError) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto Message.edit key arguments.
        Mostly used to resolve key arguments from `MenuHelpCommand.format_error_detail`.

        Parameters
        ------------
        view: HelpMenuError
            The discord.ui.View associated with the group detail.
        Returns
        --------
        :class: Dict[str, Any]
            The keyword arguments to be given onto the `Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_error_detail, view)

    async def cog_filter_commands(self,
                                  mapping: Mapping[Optional[commands.Cog], List[_Command]]
                                  ) -> Mapping[Optional[commands.Cog], List[_Command]]:
        """Retrieves a Mapping of filtered commands mapped with the Cog associated with it.

        Parameters
        ------------
        mapping: Mapping[Optional[Cog], List[Command]]
            Mapping of Cog and list of Command to be filtered.
        Returns
        --------
        :class: Mapping[Optional[Cog], List[Command]]
            A mapping of Cog and list of Command that has been filtered`.
        """
        new_mapping = {}
        for cog, cmds in mapping.items():
            filtered = await self.filter_commands(cmds, sort=self.sort_commands)
            if filtered:
                new_mapping[cog] = filtered

        return new_mapping

    async def send_bot_help(self, mapping: _MappingBotCommands, /) -> None:
        """Implementation of send bot help when a general help command was requested.

        This generally calls MenuHelpCommand.form_front_bot_menu to retrieve the interface
        and display a `discord.ui.View` given by the `HelpMenuProvider.provide_bot_view`.

        Parameters
        ------------
        mapping: Mapping[Optional[Cog], List[Command]]
            Mapping of Cog and list of Command associated with it.
        """
        filtered_commands = await self.cog_filter_commands(mapping)
        view = await self.view_provider.provide_bot_view(filtered_commands)
        menu_kwargs = await self.form_front_bot_menu_kwargs(mapping)
        menu_kwargs.setdefault("view", view)
        message = await self.get_destination().send(**menu_kwargs)
        await self.initiate_view(view=view, message=message, context=self.context)

    async def initiate_view(self, view: Optional[discord.ui.View], **kwargs: Any) -> None:
        """Initiate the view that was given by the `HelpMenuProvider`.

        This assigned the initial Message into `MenuHelpCommand.original_message`.

        Parameters
        ------------
        view: Optional[View]
            Mapping of Cog and list of Command associated with it.
        **kwargs: Any
            Key arguments to be passed onto the `Message.send` or View.start if ViewEnhanced is passed.
        """
        if isinstance(view, ViewAuthor):
            await view.start(**kwargs)
            self.original_message = view.message
            return

        self.original_message = await self.get_destination().send(view=view, **kwargs)

    async def send_cog_help(self, cog: commands.Cog, /) -> None:
        """Implementation of send cog help when a cog help command was requested.

        This generally display a `discord.ui.View` given by the `HelpMenuProvider.provide_cog_view`.

        Parameters
        ------------
        cog: commands.Cog
            The cog instance that was requested.
        """
        cmds = await self.filter_commands(cog.walk_commands(), sort=self.sort_commands)
        view = await self.view_provider.provide_cog_view(cog, cmds)
        await self.initiate_view(view, context=self.context)

    async def send_command_help(self, command: _Command, /) -> None:
        """Implementation of send command help when a command help command was requested.

        This generally display a `discord.ui.View` given by the `HelpMenuProvider.provide_command_view`.

        Parameters
        ------------
        cog: Command
            The command instance that was requested.
        """
        view = await self.view_provider.provide_command_view(command)
        await self.initiate_view(view)

    async def send_group_help(self, group: commands.Group[Any, ..., Any], /) -> None:
        """Implementation of send group help when a group help command was requested.

        This generally display a `discord.ui.View` given by the `HelpMenuProvider.provide_group_view`.

        Parameters
        ------------
        group: Group
            The group instance that was requested.
        """
        view = await self.view_provider.provide_group_view(group)
        await self.initiate_view(view)

    async def send_error_message(self, error: str, /) -> None:
        """Implementation of send error message when an error occurred within the help command.

        This generally display a `discord.ui.View` given by the `HelpMenuProvider.provide_error_view`.

        Parameters
        ------------
        error: str
            The error message that will be displayed onto the user.
        """
        view = await self.view_provider.provide_error_view(error)
        await self.initiate_view(view)

    async def format_front_bot_menu(self, mapping: _MappingBotCommands) -> _OptionalFormatReturns:
        """Interface to display a general description of all bot commands.

        When the total cog exceed `MenuHelpCommand.per_page`, they are automatically paginated.
        This is shown as the first message of the help command.

        Parameters
        ------------
        mapping: Dict[Optional[Cog], List[Command]]
            The mapping that will be displayed
        Returns
        --------
        :class: Union[discord.Embed, Dict[`str`, Any], `str`]
            The value to be display on the Message.
        """
        embed = discord.Embed(
            title="Help Command",
            description=self.context.bot.description or None,
            color=self.accent_color
        )
        data = [(cog, cmds) for cog, cmds in mapping.items()]
        data.sort(key=lambda d: self.resolve_cog_name(d[0]))
        for cog, cmds in data:
            name_resolved = self.resolve_cog_name(cog)
            value = getattr(cog, "description", None) or self.no_documentation
            name = f"{name_resolved} ({len(cmds)})"
            embed.add_field(name=name, value=value)

        return embed

    async def format_cog_page(self, view: HelpMenuCog, cmds: List[_Command]) -> _OptionalFormatReturns:
        """Interface to display a cog help command paginated with a list of cog

        When the total commands exceed `MenuHelpCommand.per_page`, they are automatically paginated.

        Parameters
        ------------
        view: HelpMenuCog
            The view associated with the Cog help.
        cmds: List[_Command]
            A list of commands that is associated with the Cog.
        Returns
        --------
        :class: Union[discord.Embed, Dict[`str`, Any], `str`]
            The value to be display on the Message.
        """
        return discord.Embed(
            title=self.resolve_cog_name(view.cog),
            description="\n".join([self.format_command_brief(cmd) for cmd in cmds]),
            color=self.accent_color
        )
