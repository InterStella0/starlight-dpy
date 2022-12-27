from __future__ import annotations

import itertools
import textwrap
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING, Type, Mapping

import discord
from discord.ext import commands

from ..views.pagination import SimplePaginationView, ViewAuthor

if TYPE_CHECKING:
    from .command import MenuHelpCommand

__all__ = (
    "MenuDropDown",
    "MenuHomeButton",
    "HelpMenuCog",
    "HelpMenuBot",
    "HelpMenuCommand",
    "HelpMenuGroup",
    "HelpMenuError"
)
_MappingBotCommands = Dict[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]]
_OptionalFormatReturns = Union[discord.Embed, Dict[str, Any], str]

class MenuDropDown(discord.ui.Select):
    """Represents a Select for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand select.

    Parameters
    -----------
    no_category: :class: `str`
        The text that will be displayed when there is no name for a category. Defaults to 'No Category'.
    no_documentation: :class: `str`
        The text that will be displayed when there is no documentation for a category.
        Defaults to 'No Documentation'.
    placeholder: :class: `str`
        The text that will be displayed on the Select placeholder.
        Defaults to 'Select a category'.
    """

    def __init__(self, *, no_category: str = "No Category",
                 no_documentation: str = "No Documentation",
                 placeholder: str = "Select a category",
                 **kwargs) -> None:
        super().__init__(placeholder=placeholder, **kwargs)
        self.__cog_mapping: Dict[Optional[str], commands.Cog] = {}
        self.selected_cog: Optional[commands.Cog] = None
        self.no_category = no_category
        self.no_documentation = no_documentation

    async def callback(self, interaction: discord.Interaction) -> None:
        resolved = self.values or [None]
        self.selected_cog = self.__cog_mapping.get(resolved[0])
        await self.view.toggle_interface(interaction)

    def create_category_option(self, cog: Optional[commands.Cog]) -> discord.SelectOption:
        """A method that creates SelectOption for a particular cog.

        Parameters
        -----------
        cog: Optional[commands.Cog]
            A cog that will be formatted. This can be None.

        Returns
        --------
        SelectOption
            The SelectOption that will be appended to the MenuDropDown.
        """
        docs = getattr(cog, "description", None) or self.no_documentation
        brief = textwrap.shorten(docs, width=90, placeholder="...")
        label = getattr(cog, "qualified_name", None) or self.no_category
        return discord.SelectOption(label=label, description=brief)

    def set_cogs(self, cogs: List[Optional[commands.Cog]]) -> None:
        options = []
        for cog in cogs:
            option = self.create_category_option(cog)
            options.append(option)
            self.__cog_mapping[option.label] = cog

        self.options = options


class MenuHomeButton(discord.ui.Button):
    """Represents a home button for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand home button and provided with the `cls_home_button`
    key arguments.

    Parameters
    -----------
    original_view: HelpMenuBot
        The view that is associated with the button for toggling.
    style: discord.ButtonStyle
        Style of the button. Defaults to `discord.ButtonStyle.green`.
    row: :class: `int`
        The row position of the button. Defaults to 2.
    """

    def __init__(self, original_view: HelpMenuBot,
                 *, style: discord.ButtonStyle = discord.ButtonStyle.green, row: int = 2, **kwargs):
        super().__init__(style=style, row=row, **kwargs)
        self.original_view = original_view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.message = None  # disable automatic item disabling behaviour
        self.view.stop()
        await self.original_view.toggle_interface(interaction)


class HelpMenuCog(SimplePaginationView):
    """Represents a cog pagination for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand home button and provided with the `cls_home_button`
    key arguments.

    Parameters
    -----------
    cog: Optional[commands.Cog]
        The cog associated with the list of data sources.
    help_command: MenuHelpCommand
        The help command that is associated with this view.
    data_source: List[List[commands.Command]]
        The chunks of commands that will be display.

    """
    def __init__(self, cog: Optional[commands.Cog], help_command: MenuHelpCommand, data_source: List[List[commands.Command]], **kwargs: Any) -> None:
        super().__init__(data_source, **kwargs)
        self._manipulate_buttons(help_command.pagination_buttons)
        self.disable_buttons_checker()
        self.cog: Optional[commands.Cog] = cog
        self.help_command: MenuHelpCommand = help_command

    def _manipulate_buttons(self, source: Mapping[str, discord.ui.Button]) -> None:
        for key, value in source.items():
            btn = getattr(self, key, None)
            if btn is None:
                continue

            self.remove_item(btn)
            if value is None:
                continue

            btn._underlying = value._underlying
            if value.row is not None:
                btn.row = value.row
            self.add_item(btn)

        self.disable_buttons_checker()

    async def format_page(self, interaction: discord.Interaction, data: List[commands.Command]) -> Dict[str, Any]:
        return await discord.utils.maybe_coroutine(self.help_command.format_cog_page, self, data)


class HelpMenuBot(SimplePaginationView):
    """Represents a cog pagination for the MenuHelpCommand that occurs when a general help command was requested.

    This class should be inherited when changing the MenuHelpCommand send_bot_help view and override
    `HelpMenuProvider.provide_bot_view`.

    Parameters
    -----------
    help_command: MenuHelpCommand
        The help command that is associated with this view.
    mapping: Dict[Optional[Cog], List[Command]]
        The full mapping of commands and Cog that will be display.
    no_category: :class: `str`
        The text that will be displayed when a cog is None. Defaults to 'No Category'.
    cog_per_page: Optional[:class: `int`]
        The amount of cogs that are displayed in a given page. Defaults to `MenuHelpCommand.per_page`.
    cls_home_button: Type[MenuHomeButton]
        The class that will be instantiate for the home button. This is to toggle the view between the list of cogs
        and the selected cog command lists. Defaults to `MenuHomeButton`.

    """

    def __init__(self, help_command: MenuHelpCommand, mapping: _MappingBotCommands,
                 *, no_category: str = "No Category", cog_per_page: Optional[int] = None,
                 cls_home_button: Type[MenuHomeButton] = MenuHomeButton, **kwargs):
        self.cog_per_page: int = cog_per_page or help_command.per_page
        super().__init__(self._paginate_cogs([*mapping]), **kwargs)
        self.navigation_buttons = ['previous_button', 'next_button']
        self._manipulate_buttons(help_command.pagination_buttons)
        self.no_category: str = no_category
        self.help_command: MenuHelpCommand = help_command
        self._dropdown: Optional[MenuDropDown] = None
        self.__mapping = mapping
        self._home_button = cls_home_button(self, label="Home")
        self.__visible: bool = False
        self._pagination_cog_view: Optional[ViewAuthor] = None
        self._rem_navigation()

    def _manipulate_buttons(self, source: Mapping[str, discord.ui.Button]) -> None:
        required = self.navigation_buttons
        remove = ['stop_button', 'start_button', 'end_button', *required]
        for key, value in source.items():
            btn = getattr(self, key, None)
            if btn is None:
                continue

            if key in remove:
                self.remove_item(btn)

            if value is None:
                continue

            if key in required:
                btn._underlying = value._underlying
                if value.row is not None:
                    btn.row = value.row
                self.add_item(btn)

        self.disable_buttons_checker()

    def _rem_navigation(self):
        if self.max_pages > 1:
            return

        for key in self.navigation_buttons:
            btn = getattr(self, key, None)
            if not btn:
                continue

            self.remove_item(btn)

    @property
    def current_dropdown(self) -> Optional[MenuDropDown]:
        """Current generated dropdown. Defaults to None before pagination starts."""
        return self._dropdown

    def _paginate_cogs(self, cogs: List[Optional[commands.Cog]]) -> List[List[Optional[commands.Cog]]]:
        return discord.utils.as_chunks(cogs, self.cog_per_page)

    def generate_dropdown(self, cogs: List[Optional[commands.Cog]], **kwargs) -> MenuDropDown:
        menu = MenuDropDown(no_category=self.no_category, **kwargs)
        menu.set_cogs(cogs)
        return menu

    async def format_view(self, interaction: Optional[discord.Interaction], data: List[Optional[commands.Cog]]) -> None:
        if not self.current_dropdown:
            row = min([getattr(self, x).row or 0 for x in self.navigation_buttons if hasattr(self, x)])
            self._dropdown = dropdown = self.generate_dropdown(data, row=None if row == 0 else row - 1)
            self.add_item(dropdown)
        else:
            self.current_dropdown.set_cogs(data)

    async def format_page(self, interaction: discord.Interaction, data: List[Optional[commands.Cog]]) -> _OptionalFormatReturns:
        mapping = {}
        for cog in data:
            mapping[cog] = self.__mapping[cog]

        return await self.help_command.form_front_bot_menu_kwargs(mapping)

    async def toggle_interface(self, interaction: discord.Interaction):
        self.__visible = not self.__visible
        if not self.__visible:
            if self._pagination_cog_view:
                self._pagination_cog_view.stop(on_stop=False)
                self._pagination_cog_view = None
            await self.change_page(interaction, self.current_page)
            return

        selected_cog = self._dropdown.selected_cog
        await interaction.response.defer()
        await self.display_cog_help(selected_cog, self.__mapping[selected_cog])

    async def display_cog_help(self, cog: Optional[commands.Cog], cmds: List[commands.Command]):
        self._pagination_cog_view = pagination = await self.help_command.view_provider.provide_cog_view(cog, cmds)
        pagination.add_item(self._home_button)
        await pagination.start(self.help_command.context, message=self.help_command.original_message)

        async def _scheduled_task(*args, **kwargs):
            self.timeout = self.timeout
            await task_callback(*args, **kwargs)

        task_callback = pagination._scheduled_task
        pagination._scheduled_task = _scheduled_task


class HelpMenuCommand(ViewAuthor):
    """Implements a View on a command for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand command menu and
    override the `HelpMenuProvider.provide_command_view`.

    Parameters
    -----------
    help_command: MenuHelpCommand
        The help command that is associated with this view.
    command: Command
        The command that will be display.

    """
    def __init__(self, help_command: MenuHelpCommand, command: commands.Command, **kwargs):
        super().__init__(**kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.command = command

    async def start(self, context: commands.Context, *args: Any, **kwargs: Any) -> None:
        help_command = self.help_command
        kwargs = await help_command.form_command_detail_kwargs(self)
        await super().start(context, *args, **kwargs)


class HelpMenuGroup(ViewAuthor):
    """Implements a View on a group for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand group menu and
    override the `HelpMenuProvider.provide_group_view`.

    Parameters
    -----------
    help_command: MenuHelpCommand
        The help command that is associated with this view.
    group: Group
        The group that will be display.

    """
    def __init__(self, help_command: MenuHelpCommand, group: commands.Group[Any, ..., Any], **kwargs):
        super().__init__(**kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.group = group

    async def start(self, context: commands.Context, *args: Any, **kwargs: Any) -> None:
        help_command = self.help_command
        kwargs = await help_command.form_group_detail_kwargs(self)
        await super().start(context, *args, **kwargs)


class HelpMenuError(ViewAuthor):
    """Implements a View on an error message for the MenuHelpCommand.

    This class should be inherited when changing the MenuHelpCommand error menu and
    override the `HelpMenuProvider.provide_error_view`.

    Parameters
    -----------
    help_command: MenuHelpCommand
        The help command that is associated with this view.
    error: str
        The error that will be display.

    """
    def __init__(self, help_command: MenuHelpCommand, error: str, **kwargs):
        super().__init__(delete_after=True, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.error = error

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def on_click_delete(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Implements a stop button for the error message.

        This essentially stop the view and defer the interaction.

        Parameters
        -----------
        interaction: discord.Interaction
            The interaction that called the button.
        button: discord.ui.Button
            The button that was clicked.

        """
        self.stop()
        await interaction.response.defer()

    async def start(self, context: commands.Context, *args: Any, **kwargs: Any) -> None:
        detail = await self.help_command.form_error_detail_kwargs(self)
        await super().start(context, *args, **detail)


class HelpMenuProvider:
    """An implementation specifically for the MenuHelpCommand.

    Its sole purpose is to provide a proper View instance depending on the command called.
    Users can subclass this class if they want to change the behaviour of the MenuHelpCommand. This should be
    supplied into the MenuHelpCommand for it to be applied properly.

    Note that this class does not send any messages. That job belongs to MenuHelpCommand to provide its interface.

    Attributes
    ------------
    help_command: :class:`MenuHelpCommand`
        The help command instance that was binded to the provider.

    """
    def __init__(self, help_command: MenuHelpCommand):
        self.help_command: MenuHelpCommand = help_command

    async def provide_bot_view(self, mapping: _MappingBotCommands) -> HelpMenuBot:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_bot_help is called.
        It provide a HelpMenuBot instance to be displayed on the help_command.

        Overriding this method requires returning HelpMenuBot to supply a view for the MenuHelpCommand.send_bot_help
        method.

        Parameters
        ------------
        mapping: Dict[Optional[:class:`Cog`], List[:class:`Command`]]
            A filtered mapping of cogs to commands that have been requested by the user for help.
            The key of the mapping is the :class:`~.commands.Cog` that the command belongs to, or
            ``None`` if there isn't one, and the value is a list of commands that belongs to that cog.

        Returns
        --------
        :class:`HelpMenuBot`
            The view for the MenuHelpCommand
        """
        help_command = self.help_command
        return HelpMenuBot(
            help_command, mapping, no_category=help_command.no_category, cls_home_button=help_command.cls_home_button
        )

    async def provide_cog_view(self, cog: commands.Cog, cog_commands: List[commands.Command]) -> HelpMenuCog:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_cog_help is called.
        It provide a HelpMenuCog instance to be displayed on the help_command.

        Overriding this method requires returning HelpMenuCog to supply a view for the MenuHelpCommand.send_cog_help
        method.

        Parameters
        ------------
        cog: :class:`Cog`
            The cog that was requested for help supplied from MenuHelpCommand.send_cog_help.
        cog_commands: List[:class:`Command`]
            Processed commands that belongs to the cog.

        Returns
        --------
        :class:`HelpMenuCog`
            The view for the MenuHelpCommand
        """
        help_command = self.help_command
        chunks = discord.utils.as_chunks(cog_commands, help_command.per_page)
        return HelpMenuCog(cog, help_command, chunks)

    async def provide_command_view(self, command: commands.Command[Any, ..., Any], /) -> HelpMenuCommand:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_command_help is called.
        It provide a HelpMenuCommand instance to be displayed on the help_command.
        This is called when the user is requesting help on a command.

        Overriding this method requires returning HelpMenuCommand to supply a view for the MenuHelpCommand.send_command_help
        method.

        Parameters
        ------------
        command: :class:`Command`
            The requested command by the user.

        Returns
        --------
        :class:`HelpMenuCommand`
            The view for the MenuHelpCommand
        """
        return HelpMenuCommand(self.help_command, command)

    async def provide_group_view(self, group: commands.Group[Any, ..., Any], /) -> HelpMenuGroup:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_group_help is called.
        It provide a HelpMenuCommand instance to be displayed on the help_command.
        This is called when the user is requesting help on a group command.

        Overriding this method requires returning HelpMenuCommand to supply a view for the MenuHelpCommand.send_command_help
        method.

        Parameters
        ------------
        group: :class:`Group`
            The requested group by the user.

        Returns
        --------
        :class:`HelpMenuGroup`
            The view for the MenuHelpCommand
        """
        return HelpMenuGroup(self.help_command, group)

    async def provide_error_view(self, error: str, /) -> HelpMenuError:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_error_help is called.
        It provide a HelpMenuError instance to be displayed on the help_command.
        This is called when there is an error occurred invoking the help command.

        Overriding this method requires returning HelpMenuCommand to supply a view for the MenuHelpCommand.send_error_help
        method.

        Parameters
        ------------
        error: str
            The error message that occurred.

        Returns
        --------
        :class:`HelpMenuError`
            The view for the MenuHelpCommand
        """
        return HelpMenuError(self.help_command, error)
