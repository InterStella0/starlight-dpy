from __future__ import annotations
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING, Type

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
    cogs: List[Cog]
        List of cogs to be shown on the dropdown.
    no_category: :class: `str`
        The text that will be displayed when
    """

    def __init__(self, cogs: List[Optional[commands.Cog]], *, no_category: str = "No Category", **kwargs) -> None:
        super().__init__(**kwargs)
        self.__cog_selections: List[Optional[commands.Cog]] = cogs
        self.__cog_mapping: Dict[Optional[str], commands.Cog] = {}
        self.selected_cog: Optional[commands.Cog] = None
        self.no_category = no_category
        self.__create_dropdowns()

    async def callback(self, interaction: discord.Interaction) -> None:
        resolved = self.values or [None]
        self.selected_cog = self.__cog_mapping.get(resolved[0])
        await self.view.toggle_interface(interaction)

    def form_category_option(self, cog: Optional[commands.Cog]) -> Dict[str, Any]:
        """Format for a cog that will be passed onto the SelectOption.

        Parameters
        -----------
        cog: Optional[commands.Cog]
            A cog that will be formatted. This can be None.

        Returns
        --------
         Dict[`str`, Any]
            The dictionary that will be passed as a SelectOption key arguments.
        """
        return dict(label=getattr(cog, "qualified_name", None) or self.no_category)

    def __create_dropdowns(self) -> None:
        for cog in self.__cog_selections:
            option = discord.SelectOption(**self.form_category_option(cog))
            self.append_option(option)
            self.__cog_mapping.update({option.label: cog})


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
    """

    def __init__(self, original_view: HelpMenuBot, *, style: discord.ButtonStyle = discord.ButtonStyle.green, **kwargs):
        super().__init__(style=style, **kwargs)
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
        btns = help_command.pagination_buttons
        self.start_button = btns.get('start_button')
        self.previous_button = btns.get('previous_button')
        self.stop_button = btns.get('stop_button')
        self.next_button = btns.get('next_button')
        self.end_button = btns.get('end_button')
        super().__init__(data_source, **kwargs)
        self.cog: Optional[commands.Cog] = cog
        self.help_command: MenuHelpCommand = help_command

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
    start_button = end_button = stop_button = None
    previous_button: Optional[discord.ui.Button] = discord.utils.MISSING
    next_button: Optional[discord.ui.Button] = discord.utils.MISSING

    def __init__(self, help_command: MenuHelpCommand, mapping: _MappingBotCommands,
                 *, no_category: str = "No Category", cog_per_page: Optional[int] = None,
                 cls_home_button: Type[MenuHomeButton] = MenuHomeButton, **kwargs):
        self.cog_per_page: int = cog_per_page or help_command.per_page
        btns = help_command.pagination_buttons
        self.previous_button = btns.get('previous_button')
        self.next_button = btns.get('next_button')
        super().__init__(self._paginate_cogs([*mapping]), **kwargs)
        self.no_category: str = no_category
        self.help_command: MenuHelpCommand = help_command
        self._dropdown: Optional[MenuDropDown] = None
        self.__mapping = mapping
        self._home_button = cls_home_button(self, label="Home")
        self.__visible: bool = False
        self.remove_item(self.previous_button)
        self.remove_item(self.next_button)

    def _paginate_cogs(self, cogs: List[Optional[commands.Cog]]) -> List[List[Optional[commands.Cog]]]:
        return discord.utils.as_chunks(cogs, self.cog_per_page)

    def _generate_dropdown(self, cogs: List[Optional[commands.Cog]], **kwargs) -> MenuDropDown:
        return MenuDropDown(cogs, no_category=self.no_category, **kwargs)

    def _generate_navigation(self):
        if self.max_pages > 1:
            for btn in (self.previous_button, self.next_button):
                if btn in self.children:
                    self.remove_item(btn)
                self.add_item(btn)

    async def format_page(self, interaction: discord.Interaction, data: List[Optional[commands.Cog]]) -> _OptionalFormatReturns:
        mapping = {}
        for cog in data:
            mapping[cog] = self.__mapping[cog]

        if self._dropdown:
            self.remove_item(self._dropdown)

        self._dropdown = self._generate_dropdown([*mapping])
        self.add_item(self._dropdown)
        self._generate_navigation()
        return await self.help_command.form_front_bot_menu_kwargs(mapping)

    async def toggle_interface(self, interaction: discord.Interaction):
        self.__visible = not self.__visible
        if not self.__visible:
            await self.change_page(interaction, self.current_page)
            return

        selected_cog = self._dropdown.selected_cog
        await interaction.response.defer()
        await self.display_cog_help(selected_cog, self.__mapping[selected_cog])

    async def display_cog_help(self, cog: Optional[commands.Cog], cmds: List[commands.Command]):
        pagination = await self.help_command.view_provider.provide_cog_view(cog, cmds)
        pagination.add_item(self._home_button)
        await pagination.start(self.help_command.context, message=self.help_command.original_message)


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
        super().__init__(context=help_command.context, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.command = command

    async def start(self):
        help_command = self.help_command
        kwargs = await help_command.form_command_detail_kwargs(self)
        await super().start(**kwargs)


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
        super().__init__(context=help_command.context, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.group = group

    async def start(self):
        help_command = self.help_command
        kwargs = await help_command.form_group_detail_kwargs(self)
        await super().start(**kwargs)


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
        super().__init__(delete_after=True, context=help_command.context, **kwargs)
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

    async def start(self) -> None:
        detail = await self.help_command.form_error_detail_kwargs(self)
        await super().start(**detail)


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
