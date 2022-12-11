from __future__ import annotations
from typing import Optional, List, Any, Union, Dict, TypeVar, Mapping

import discord
from discord.ext import commands

from .views import SimplePaginationView, ViewEnchanced

__all__ = (
    "MenuHelpCommand",
)

T = TypeVar('T')


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

    def __init__(self, help_command: MenuHelpCommand, mapping: Dict[Optional[commands.Cog], commands.Command],
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

    async def format_page(self, interaction: discord.Interaction, data: List[commands.Cog]) -> Union[discord.Embed, Dict[str, Any], str]:
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

    async def provide_bot_view(self, mapping: Dict[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]]) -> HelpMenuBot:
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


class MenuHelpCommand(commands.MinimalHelpCommand):
    def __init__(self, *,
                 per_page: int = 6,
                 cog_menu: bool = True,
                 sort_commands: bool = True,
                 no_documentation: str = "No Documentation",
                 accent_color: Union[discord.Color, int] = discord.Color.blurple(),
                 error_color: Union[discord.Color, int] = discord.Color.red()):
        super().__init__()
        self.per_page: int = per_page
        self._cog_menu: bool = cog_menu
        self.accent_color: Union[discord.Color, int] = accent_color
        self.error_color: Union[discord.Color, int] = error_color
        self.no_documentation = no_documentation
        self.__sort_commands: bool = sort_commands
        self.view_provider: HelpMenuProvider = HelpMenuProvider(self)
        self.original_message: Optional[discord.Message] = None

    def format_command_brief(self, cmd: commands.Command) -> str:
        return f"{self.get_command_signature(cmd)}\n{cmd.short_doc or self.no_documentation}"

    async def format_group_detail(self, view: HelpMenuGroup) -> Union[discord.Embed, Dict[str, Any], str]:
        group = view.group
        subcommands = "\n".join([self.format_command_brief(cmd) for cmd in group.commands])
        description = group.help or self.no_documentation
        return discord.Embed(
            title=self.get_command_signature(group),
            description=f"{description}\n\n**Subcommands**\n{subcommands}",
            color=self.accent_color
        )

    async def format_command_detail(self, view: HelpMenuCommand) -> discord.Embed:
        cmd = view.command
        return discord.Embed(
            title=self.get_command_signature(cmd),
            description=cmd.help,
            color=self.accent_color
        )

    async def format_error_detail(self, view: HelpMenuError) -> discord.Embed:
        return discord.Embed(
            title="Something went wrong!",
            description=str(view.error),
            color=self.error_color
        )

    def resolve_cog_name(self, cog: Optional[commands.Cog]):
        return getattr(cog, "qualified_name", None) or self.no_category

    async def __normalized_kwargs(self, callback, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        formed_interface = await discord.utils.maybe_coroutine(callback, *args, **kwargs)
        if isinstance(formed_interface, dict):
            return formed_interface
        elif isinstance(formed_interface, discord.Embed):
            return {"embed": formed_interface}
        return {"content": formed_interface}

    async def _form_front_bot_menu(self, cogs: List[commands.Cog]) -> Dict[str, Any]:
        return await self.__normalized_kwargs(self.format_front_bot_menu, cogs)

    async def _form_command_detail(self, view: HelpMenuCommand) -> Dict[str, Any]:
        return await self.__normalized_kwargs(self.format_command_detail, view)

    async def _form_group_detail(self, view: HelpMenuGroup) -> Dict[str, Any]:
        return await self.__normalized_kwargs(self.format_group_detail, view)

    async def _form_error_detail(self, view: HelpMenuError) -> Dict[str, Any]:
        return await self.__normalized_kwargs(self.format_error_detail, view)

    async def _filter_commands(self,
                               mapping: Mapping[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]]
                               ) -> Mapping[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]]:
        for cog, cmds in mapping.items():
            filtered = await self.filter_commands(cmds, sort=self.__sort_commands)
            if filtered:
                yield cog, filtered

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command[Any, ..., Any]]], /) -> None:
        filtered_commands = {cog: cmds async for cog, cmds in self._filter_commands(mapping)}
        view = await self.view_provider.provide_bot_view(filtered_commands)
        menu_kwargs = await self._form_front_bot_menu(mapping) if self._cog_menu else {}
        menu_kwargs.setdefault("view", view)
        message = await self.get_destination().send(**menu_kwargs)
        await self.initiate_view(view=view, message=message, context=self.context)

    async def initiate_view(self, view: Optional[ViewEnchanced], **kwargs):
        if isinstance(view, ViewEnchanced):
            await view.start(**kwargs)
            self.original_message = view.message
            return

        self.original_message = await self.get_destination().send(view=view, **kwargs)

    async def send_cog_help(self, cog: commands.Cog, /) -> None:
        cmds = await self.filter_commands(cog.walk_commands(), sort=self.__sort_commands)
        view = await self.view_provider.provide_cog_view(cog, cmds)
        await self.initiate_view(view)

    async def send_command_help(self, command: commands.Command[Any, ..., Any], /) -> None:
        view = await self.view_provider.provide_command_view(command)
        await self.initiate_view(view)

    async def send_group_help(self, group: commands.Group[Any, ..., Any], /) -> None:
        view = await self.view_provider.provide_group_view(group)
        await self.initiate_view(view)

    async def send_error_message(self, error: str, /) -> None:
        view = await self.view_provider.provide_error_view(error)
        await self.initiate_view(view)

    async def format_front_bot_menu(self, mapping: Dict[Optional[commands.Cog], commands.Command[Any, ..., Any]]
                                    ) -> Union[discord.Embed, Dict[str, Any], str]:
        embed = discord.Embed(
            title="Help Command",
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

    async def format_cog_page(self, view: HelpMenuCog, data: List[commands.Command]) -> Union[discord.Embed, Dict[str, Any], str]:
        return discord.Embed(
            title=self.resolve_cog_name(view.cog),
            description="\n".join([self.format_command_brief(cmd) for cmd in data]),
            color=self.accent_color
        )
