from __future__ import annotations

import itertools
from typing import Optional, List, Any, Union, Dict, TypeVar, Mapping, Type

import discord
from discord.ext import commands

from .view import HelpMenuCommand, HelpMenuProvider, HelpMenuGroup, HelpMenuError, HelpMenuCog, MenuHomeButton, \
    HelpPaginateProvider, HelpPaginateBot, HelpMenuBot
from ..views.pagination import ViewAuthor

__all__ = (
    "MenuHelpCommand",
    "PaginateHelpCommand",
)

T = TypeVar('T')
_Command = commands.Command[Any, ..., Any]
_MappingBotCommands = Dict[Optional[commands.Cog], List[_Command]]
_OptionalFormatReturns = Union[discord.Embed, Dict[str, Any], str]


class MenuHelpCommand(commands.HelpCommand):
    """HelpCommand implementation for MenuHelpCommand which utilizes :class:`discord.ui.Select`
    for :class:`commands.Cog` selection and :class:`discord.ui.Button` for command pagination.

    Attributes
    ------------
    per_page: :class:`int`
        Amount of items per page that are displayed. This applies to Cog menu and command pagination. Defaults to 6.

    sort_commands: :class:`bool`
        Sort commands in ascending order based on the command name. Default to True.

    no_documentation: :class:`str`
        Text displayed when a command does not have a command description. Defaults to 'No Documentation'.

    no_category: :class:`str`
        Text display for commands that does not have a Cog associated with it. Defaults to 'No Category'

    accent_color: :class:`str`
        Color of embed for normal display. Defaults to :class:`discord.Color.blurple`.

    error_color: Union[:class:`discord.Colour`, :class:`int`]
        Color of embed for error display. Defaults to :class:`discord.Color.red`.

    pagination_buttons: Optional[Mapping[ :class:`str`, :class:`discord.ui.Button`]]
        Mapping of pagination discord.ui.Button instances for each pagination iteraction.

    inline_fields: :class:`bool`
        Boolean that indicate if embed field on cog should be inline. Defaults to True.

    cls_home_button: Type[:class:`MenuHomeButton`]
        :class:`discord.ui.Button` class for the home button.
    view_provider: :class:`HelpMenuProvider`
        An instance that provides View for each command use cases. Best way to give custom a
        :class:`discord.ui.View` onto the :class:`MenuHelpCommand`.
    original_message: Optional[:class:`discord.Message`]
        A Message instance that was initially sent by the :class:`MenuHelpCommand`.
    """

    def __init__(self, *,
                 per_page: int = 6,
                 sort_commands: bool = True,
                 no_documentation: str = "No Documentation",
                 no_category: str = "No Category",
                 accent_color: Union[discord.Color, int] = discord.Color.blurple(),
                 error_color: Union[discord.Color, int] = discord.Color.red(),
                 pagination_buttons: Optional[Mapping[str, discord.ui.Button]] = None,
                 inline_fields: bool = True,
                 cls_home_button: Type[MenuHomeButton] = MenuHomeButton,
                 **options):
        super().__init__(**options)
        self.no_category: str = no_category
        self.per_page: int = per_page
        self.inline_fields = inline_fields
        self.accent_color: Union[discord.Color, int] = accent_color
        self.error_color: Union[discord.Color, int] = error_color
        self.no_documentation: str = no_documentation
        self.sort_commands: bool = sort_commands
        self.view_provider: HelpMenuProvider = HelpMenuProvider(self)
        self.original_message: Optional[discord.Message] = None
        self.pagination_buttons = pagination_buttons
        self.cls_home_button = cls_home_button

    @property
    def pagination_buttons(self) -> Mapping[str, Optional[discord.ui.Button]]:
        """Your pagination button configuration that will be used for each pagination views within this help command."""
        row = 1
        return self._pagination_buttons or {
            "start_button": discord.ui.Button(emoji="⏪", row=row),
            "previous_button": discord.ui.Button(emoji="◀️", row=row),
            "stop_button": discord.ui.Button(emoji="⏹️", row=row),
            "next_button": discord.ui.Button(emoji="▶️", row=row),
            "end_button": discord.ui.Button(emoji="⏩", row=row)
        }

    @pagination_buttons.setter
    def pagination_buttons(self, value: Mapping[str, discord.ui.Button]):
        self._pagination_buttons = value

    def get_command_signature(self, command: _Command, /) -> str:
        """Retrieves the Command signature during Command pagination.

        Parameters
        ------------
        command: :class:`commands.Command`
            The command to get the signature of.

        Returns
        --------
        :class:`str`
            The signature for the command.
        """
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'

    def format_command_brief(self, command: _Command) -> str:
        """Retrieves the Command signature with a brief description during Command pagination.

        Parameters
        ------------
        command: :class:`commands.Command`
            The command to get the signature of.
        Returns
        --------
        :class:`str`
            The signature for the command.
        """
        return f"`{self.get_command_signature(command)}`\n{command.short_doc or self.no_documentation}"

    async def format_group_detail(self, view: HelpMenuGroup) -> _OptionalFormatReturns:
        """Interface to display a detail description of a Group command.

        Parameters
        ------------
        view: :class:`HelpMenuGroup`
            The view that is associated with the Message.

        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
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
        view: :class:`HelpMenuCommand`
            The view that is associated with the Message.
        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
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
        view: :class:`HelpMenuError`
            The view that is associated with the error Message.
        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
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
        cog: Optional[:class:`commands.Cog`]
            The cog to resolve the name.
        Returns
        --------
        :class:`str`
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

    async def form_bot_kwargs(self, view: HelpMenuBot, mapping: _MappingBotCommands) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto :meth:`discord.Message.edit` key arguments.
        Mostly used to resolve key arguments from `MenuHelpCommand.form_front_bot_menu`.

        Parameters
        ------------
        view: :class:`HelpMenuBot`
            The view paginator that is used.
        mapping: Dict[Optional[:class:`commands.Cog`], List[:class:`commands.Command`]]
            The dictionary that is mapped on Cog and the list Command associated with it.
        Returns
        --------
        Dict[:class:`str`, Any]
            The keyword arguments to be given onto the `:meth:`discord.Message.edit``.
        """
        return await self.__normalized_kwargs(self.format_bot_page, view, mapping)

    async def form_command_detail_kwargs(self, view: HelpMenuCommand) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto :meth:`discord.Message.edit` key arguments.
        Mostly used to resolve key arguments from :meth:`MenuHelpCommand.format_command_detail`.

        Parameters
        ------------
        view: :class:`HelpMenuCommand`
            The :class:`discord.ui.View` associated with the command detail.
        Returns
        --------
        Dict[:class:`str`, Any]
            The keyword arguments to be given onto the :meth:`discord.Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_command_detail, view)

    async def form_group_detail_kwargs(self, view: HelpMenuGroup) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto :meth:`discord.Message.edit` key arguments.
        Mostly used to resolve key arguments from :meth:`MenuHelpCommand.format_group_detail`.

        Parameters
        ------------
        view: :class:`HelpMenuGroup`
            The :class:`discord.ui.View` associated with the group detail.
        Returns
        --------
        Dict[:class:`str`, Any]
            The keyword arguments to be given onto the :class::meth:`discord.Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_group_detail, view)

    async def form_error_detail_kwargs(self, view: HelpMenuError) -> Dict[str, Any]:
        """Retrieves a Dictionary that can be directly used onto :meth:`discord.Message.edit` key arguments.
        Mostly used to resolve key arguments from :meth:`MenuHelpCommand.format_error_detail`.

        Parameters
        ------------
        view: HelpMenuError
            The discord.ui.View associated with the group detail.
        Returns
        --------
        Dict[str, Any]
            The keyword arguments to be given onto the `:meth:`discord.Message.edit`.
        """
        return await self.__normalized_kwargs(self.format_error_detail, view)

    async def cog_filter_commands(self,
                                  mapping: Mapping[Optional[commands.Cog], List[_Command]]
                                  ) -> Mapping[Optional[commands.Cog], List[_Command]]:
        """Retrieves a Mapping of filtered commands mapped with the Cog associated with it.

        Parameters
        ------------
        mapping: Mapping[Optional[:class:`commands.Cog`], List[:class:`commands.Command`]]
            Mapping of Cog and list of Command to be filtered.
        Returns
        --------
        Mapping[Optional[:class:`commands.Cog`], List[:class:`commands.Command`]]
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
        mapping: Mapping[Optional[:class:`commands.Cog`], List[:class:`commands.Command`]]
            Mapping of Cog and list of Command associated with it.
        """
        filtered_commands = await self.cog_filter_commands(mapping)
        view = await self.view_provider.provide_bot_view(filtered_commands)
        await self.initiate_view(view)

    async def initiate_view(self, view: Optional[discord.ui.View], **kwargs: Any) -> None:
        """Initiate the view that was given by the :class:`HelpMenuProvider`.

        This assigned the initial Message into :attr:`MenuHelpCommand.original_message`.

        Parameters
        ------------
        view: Optional[View]
            Mapping of Cog and list of Command associated with it.
        **kwargs: Any
            Key arguments to be passed onto the :meth:`discord.Message.send` or :meth:`discord.ui.View.start`
            if :class:`ViewAuthor` was passed.
        """
        if isinstance(view, ViewAuthor):
            await view.start(self.context, **kwargs)
            self.original_message = view.message
            return

        self.original_message = await self.get_destination().send(view=view, **kwargs)

    async def send_cog_help(self, cog: commands.Cog, /) -> None:
        """Implementation of send cog help when a cog help command was requested.

        This generally display a `discord.ui.View` given by the :meth:`HelpMenuProvider.provide_cog_view`.

        Parameters
        ------------
        cog: commands.Cog
            The cog instance that was requested.
        """
        cmds = await self.filter_commands(cog.walk_commands(), sort=self.sort_commands)
        view = await self.view_provider.provide_cog_view(cog, cmds)
        await self.initiate_view(view)

    async def send_command_help(self, command: _Command, /) -> None:
        """Implementation of send command help when a command help command was requested.

        This generally display a :class:`discord.ui.View` given by the :meth:`HelpMenuProvider.provide_command_view`.

        Parameters
        ------------
        command: :class:`commands.Command`
            The command instance that was requested.
        """
        view = await self.view_provider.provide_command_view(command)
        await self.initiate_view(view)

    async def send_group_help(self, group: commands.Group[Any, ..., Any], /) -> None:
        """Implementation of send group help when a group help command was requested.

        This generally display a :class:`discord.ui.View` given by the :meth:`HelpMenuProvider.provide_group_view`.

        Parameters
        ------------
        group: :class:`commands.Group`
            The group instance that was requested.
        """
        view = await self.view_provider.provide_group_view(group)
        await self.initiate_view(view)

    async def send_error_message(self, error: str, /) -> None:
        """Implementation of send error message when an error occurred within the help command.

        This generally display a :class:`discord.ui.View` given by the :meth:`HelpMenuProvider.provide_error_view`.

        Parameters
        ------------
        error: :class:`str`
            The error message that will be displayed onto the user.
        """
        view = await self.view_provider.provide_error_view(error)
        await self.initiate_view(view)

    async def format_bot_page(self, view: HelpMenuBot, mapping: _MappingBotCommands) -> _OptionalFormatReturns:
        """Interface to display a general description of all bot commands.

        When the total cog exceed `MenuHelpCommand.per_page`, they are automatically paginated.
        This is shown as the first message of the help command.

        Parameters
        ------------
        view: :class:`HelpMenuBot`
            The view paginator that is used.
        mapping: Dict[Optional[:class:`commands.Cog`], List[:class:`commands.Command`]]
            The mapping that will be displayed.
        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
            The value to be display on the Message.
        """
        title="Help Command"
        if view.max_pages > 1:
            title += f" ({view.current_page + 1}/{view.max_pages})"

        embed = discord.Embed(
            title=title,
            description=self.context.bot.description if view.current_page == 0 else None,
            color=self.accent_color
        )
        data = [(cog, cmds) for cog, cmds in mapping.items()]
        data.sort(key=lambda d: self.resolve_cog_name(d[0]))
        for cog, cmds in data:
            name_resolved = self.resolve_cog_name(cog)
            value = getattr(cog, "description", None) or self.no_documentation
            name = f"{name_resolved} (`{len(cmds)}`)"
            embed.add_field(name=name, value=value, inline=self.inline_fields)

        return embed

    async def format_cog_page(self, view: HelpMenuCog, cmds: List[_Command]) -> _OptionalFormatReturns:
        """Interface to display a cog help command paginated with a list of cog

        When the total commands exceed :attr:`MenuHelpCommand.per_page`, they are automatically paginated.

        Parameters
        ------------
        view: :class:HelpMenuCog
            The view associated with the Cog help.
        cmds: List[:class:`commands.Command`]
            A list of commands that is associated with the Cog.
        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
            The value to be display on the Message.
        """

        title = f"{self.resolve_cog_name(view.cog)} ({view.current_page + 1}/{view.max_pages})"
        desc = ""
        if view.current_page == 0:
            desc = getattr(view.cog, "description", None) or self.no_documentation
            all_cmds = [*itertools.chain.from_iterable(view.data_source)]
            desc += f"\n\n**Commands[`{len(all_cmds)}`]**\n"

        list_cmds = "\n".join([self.format_command_brief(cmd) for cmd in cmds])
        return discord.Embed(
            title=title,
            description=f"{desc}{list_cmds}",
            color=self.accent_color
        )


class PaginateHelpCommand(MenuHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.view_provider = HelpPaginateProvider(self)

    async def format_bot_page(self, view: HelpPaginateBot, cmds: List[_Command]) -> _OptionalFormatReturns:
        """Interface to display a general description of all bot commands.

        When the total cog exceed :attr:`PaginateHelpCommand.per_page`, they are automatically paginated.
        This is shown as the first message of the help command.

        Parameters
        ------------
        view: :class:`HelpPaginateBot`
            The view paginator that is used.
        cmds: List[:class:`commands.Command`]
            The list of commands for each page.
        Returns
        --------
        Union[:class:`discord.Embed`, Dict[:class:`str`, Any], :class:`str`]
            The value to be display on the Message.
        """
        current_page = view.current_page
        first_cmd = cmds[0]
        return discord.Embed(
            title=f"Help Command ({self.resolve_cog_name(first_cmd.cog)}) [{current_page + 1}/{view.max_pages}]",
            description="\n".join([self.format_command_brief(c) for c in cmds]),
            color=self.accent_color
        )
