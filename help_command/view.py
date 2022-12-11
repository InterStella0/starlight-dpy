from __future__ import annotations
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING

import discord
from discord.ext import commands

from ..views.pagination import SimplePaginationView, ViewEnchanced

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
    def __init__(self, cogs: List[commands.Cog], *, no_category: str = "No Category", **kwargs):
        super().__init__(**kwargs)
        self.__cog_selections: List[commands.Cog] = cogs
        self.__cog_mapping: Dict[Optional[str], commands.Cog] = {}
        self.selected_cog: Optional[commands.Cog] = None
        self.no_category = no_category
        self.__create_dropdowns()

    async def callback(self, interaction: discord.Interaction) -> Any:
        resolved = self.values or [None]
        self.selected_cog = self.__cog_mapping.get(resolved[0])
        await self.view.toggle_interface(interaction)

    def form_category_option(self, cog: Optional[commands.Cog]):
        return dict(label=getattr(cog, "qualified_name", None) or self.no_category)

    def __create_dropdowns(self):
        for cog in self.__cog_selections:
            option = discord.SelectOption(**self.form_category_option(cog))
            self.append_option(option)
            self.__cog_mapping.update({option.label: cog})


class MenuHomeButton(discord.ui.Button):
    def __init__(self, original_view: HelpMenuBot, **kwargs):
        super().__init__(**kwargs)
        self.original_view = original_view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.message = None  # disable automatic item disabling behaviour
        self.view.stop()
        await self.original_view.toggle_interface(interaction)


class HelpMenuCog(SimplePaginationView):
    def __init__(self, cog: Optional[commands.Cog], help_command: MenuHelpCommand, data_source: List[commands.Command], **kwargs):
        super().__init__(data_source, **kwargs)
        self.cog: Optional[commands.Cog] = cog
        self.help_command: MenuHelpCommand = help_command

    async def format_page(self, interaction: discord.Interaction, data: List[commands.Command]) -> Dict[str, Any]:
        return await discord.utils.maybe_coroutine(self.help_command.format_cog_page, self, data)


class HelpMenuBot(SimplePaginationView):
    start_button = end_button = stop_button = None
    previous_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="◀️")
    next_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="▶️")

    def __init__(self, help_command: MenuHelpCommand, mapping: _MappingBotCommands,
                 *, no_category: str = "No Category", cog_per_page: Optional[int] = None, **kwargs):
        self.cog_per_page: int = cog_per_page or help_command.per_page
        super().__init__(self._paginate_cogs([*mapping]), context=help_command.context, **kwargs)
        self.no_category: str = no_category
        self.help_command: MenuHelpCommand = help_command
        self._dropdown: Optional[MenuDropDown] = None
        self.__mapping = mapping
        self._home_button = MenuHomeButton(self, label="Home")
        self.__visible: bool = False
        self.remove_item(self.previous_button)
        self.remove_item(self.next_button)

    def _paginate_cogs(self, cogs: List[Optional[commands.Cog]]) -> List[List[Optional[commands.Cog]]]:
        return discord.utils.as_chunks(cogs, self.cog_per_page)

    def _generate_dropdown(self, cogs: List[commands.Cog], **kwargs) -> MenuDropDown:
        return MenuDropDown(cogs, no_category=self.no_category, **kwargs)

    def _generate_navigation(self):
        if self.max_pages > 1:
            for btn in (self.previous_button, self.next_button):
                if btn in self.children:
                    self.remove_item(btn)
                self.add_item(btn)

    async def format_page(self, interaction: discord.Interaction, data: List[commands.Cog]) -> _OptionalFormatReturns:
        mapping = {}
        for cog in data:
            mapping[cog] = self.__mapping[cog]

        if self._dropdown:
            self.remove_item(self._dropdown)

        self._dropdown = self._generate_dropdown([*mapping])
        self.add_item(self._dropdown)
        self._generate_navigation()
        return await self.help_command._form_front_bot_menu(mapping)

    async def toggle_interface(self, interaction: discord.Interaction):
        self.__visible = not self.__visible
        if not self.__visible:
            await self.change_page(interaction, self.current_page)
            return

        selected_cog = self._dropdown.selected_cog
        await interaction.response.defer()
        await self.display_cog_help(selected_cog, self.__mapping[selected_cog])

    async def display_cog_help(self, cog: Optional[commands.Cog], cmds: List[commands.Command]):
        chunks = discord.utils.as_chunks(cmds, self.help_command.per_page)
        pagination = HelpMenuCog(cog, self.help_command, chunks)
        pagination.add_item(self._home_button)
        await pagination.start(self.help_command.context, message=self.help_command.original_message)


class HelpMenuCommand(ViewEnchanced):
    def __init__(self, help_command: MenuHelpCommand, command: commands.Command, **kwargs):
        super().__init__(context=help_command.context, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.command = command

    async def start(self):
        help_command = self.help_command
        kwargs = await help_command._form_command_detail(self)
        await super().start(**kwargs)


class HelpMenuGroup(ViewEnchanced):
    def __init__(self, help_command: MenuHelpCommand, group: commands.Group[Any, ..., Any], **kwargs):
        super().__init__(context=help_command.context, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.group = group

    async def start(self):
        help_command = self.help_command
        kwargs = await help_command._form_group_detail(self)
        await super().start(**kwargs)


class HelpMenuError(ViewEnchanced):
    def __init__(self, help_command: MenuHelpCommand, error: Exception, **kwargs):
        super().__init__(delete_after=True, context=help_command.context, **kwargs)
        self.help_command: MenuHelpCommand = help_command
        self.error = error

    @discord.ui.button(label="Stop")
    async def on_click_delete(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.defer()

    async def start(self, context: commands.Context) -> None:
        detail = await self.help_command._form_error_detail(self)
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
        return HelpMenuBot(self.help_command, mapping, no_category=self.help_command.no_category)

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

    async def provide_error_view(self, error: Exception, /) -> HelpMenuError:
        """|coro|

        This method is invoke when the MenuHelpCommand.send_error_help is called.
        It provide a HelpMenuError instance to be displayed on the help_command.
        This is called when there is an error occurred invoking the help command.

        Overriding this method requires returning HelpMenuCommand to supply a view for the MenuHelpCommand.send_error_help
        method.

        Parameters
        ------------
        error: Exception
            The error that occurred.

        Returns
        --------
        :class:`HelpMenuError`
            The view for the MenuHelpCommand
        """
        return HelpMenuError(self.help_command, error)