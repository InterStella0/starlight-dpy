import asyncio
import copy
from typing import List, Any, TypeVar, Union, Dict, Optional

import discord
from discord.ext import commands

from ..errors.view import NotViewOwner


__all__ = (
    "SimplePaginationView",
    "ViewAuthor"
)


T = TypeVar('T')


class ViewAuthor(discord.ui.View):
    """Implementation of View that has an associated owner and handles message sending.

    Parameters
    ------------
    context: Context
       Context that is associated with this view.
    delete_after: :class: `bool`
        Indicate whether to delete the message after it has been stopped or timeout. Defaults to False.
    """
    def __init__(self, context: commands.Context, *, delete_after: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.delete_after: bool = delete_after
        self.context: commands.Context = context
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        """Implements a check whenever interaction is dispatched onto the View.

        Parameters
        ------------
        interaction: Interaction
           Interaction that triggered the view.

        Raises
        -------
        NotViewOwner
            Triggered when the interaction is unauthorized.

        Returns
        --------
        :class: `bool`
            The boolean to allow the interaction to invoke the item callback.

        """
        if interaction.user == self.context.author:
            return True

        raise NotViewOwner("You cannot interact with this message.")

    def stop(self) -> None:
        super().stop()
        asyncio.create_task(self.on_stop())

    async def on_stop(self):
        if self.message is None:
            return

        if self.delete_after:
            await self.message.delete(delay=0)
            return

        for child in self.children:
            child.disabled = True

        await self.message.edit(view=self)

    async def start(self, *args: Any, **kwargs: Any) -> None:
        """Starts the view by sending a message

        This should assign the message that was sent with the view.
        """
        self.message = await self.context.send(*args, view=self, **kwargs)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any], /) -> None:
        """Implementation of on_error if an error occurred during the interaction.

        Parameters
        ------------
        interaction: Interaction
           Interaction that triggered the view.
        error: Exception
            Error that occurred.
        item: Item
            The item that is associated during the error occurrance.
        """
        if isinstance(error, NotViewOwner):
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await super().on_error(interaction, error, item)


class SimplePaginationView(ViewAuthor):
    """Implementation View pagination that is written purely without any external library.

    This is a simple pagination view without chunking. Chunking of your data should be done before passing into this
    view.

    Parameters
    ------------
    data_source: List[`T`]
       The data source that was paginated before hand.
    delete_after: :class: `bool`
        Indicate whether to delete the message after it has been stopped or timeout. Defaults to False.

    Attributes
    -----------
    start_button: Optional[discord.ui.Button]
        The button that will set the page onto the first page. This can be overwritten during class definition.
    previous_button: Optional[discord.ui.Button]
        The button that will set the page onto the previous page. This can be overwritten during class definition.
    stop_button: Optional[discord.ui.Button]
        The button that will stop the View. This can be overwritten during class definition.
    next_button: Optional[discord.ui.Button]
        The button that will set the page onto the next page. This can be overwritten during class definition.
    end_button: Optional[discord.ui.Button]
        The button that will set the page onto the last page. This can be overwritten during class definition.
    context: Optional[Context]
        The context that is associated with this pagination view.
    message: Optional[Message]
        The initial message that was sent to the user to be overwritten every interaction.
    """
    start_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏪")
    previous_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="◀️")
    stop_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏹️")
    next_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="▶️")
    end_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏩")

    def __init__(self, data_source: List[T], /, *, delete_after: bool = False, **kwargs: Any):
        super().__init__(context=None, delete_after=delete_after, **kwargs)
        copy_data_source = [*data_source]
        self._data_source: List[T] = copy_data_source
        self.__max_pages: int = len(copy_data_source)
        self.__current_page: int = 0
        self.message: Optional[discord.Message] = None
        self.context: Optional[commands.Context] = None
        self._configuration: Dict[str, discord.ui.Button] = {}
        self._init_configuration()

    def _default_configuration(self) -> None:
        valid = {"start_button", "stop_button", "next_button", "end_button", "previous_button"}
        for key, value in SimplePaginationView.__dict__.items():
            cls_value = type(self).__dict__.get(key, discord.utils.MISSING)
            instance_value = self.__dict__.get(key, discord.utils.MISSING)
            if instance_value is discord.utils.MISSING:
                instance_value = cls_value

            if key in valid:
                if isinstance(instance_value, discord.ui.Button):
                    self._configuration.update({key: copy.deepcopy(instance_value)})
                elif instance_value is discord.utils.MISSING:
                    self._configuration.update({key: copy.deepcopy(value)})

    def _init_configuration(self) -> None:
        self._default_configuration()
        for name, button in self._configuration.items():
            button_name, _, suffix = name.partition("_")
            if suffix.casefold() != "button":
                continue

            callback = getattr(self, "to_" + button_name, None)
            if callback is None:
                raise AttributeError(f"'{name}' is an invalid configuration.")

            button.callback = callback
            button._view = self
            setattr(self, callback.__name__, button)
            self.add_item(button)

        self.disable_buttons_checker()

    @property
    def current_page(self) -> int:
        """The current page of the pagination view."""
        return self.__current_page

    @property
    def max_pages(self) -> int:
        """The maximum page of the pagination view that was given."""
        return self.__max_pages

    async def start(self, context: commands.Context, *, wait: bool = False, message: Optional[discord.Message] = None) -> None:
        """Initiate the pagination view by sending the message or editing the message when Message is present.

        Parameters
        ------------
        context: `Context`
            The context associated with the interaction.
        wait: :class: `bool`
            Indicates whether to wait until the pagination finishes. Default to False.
        message: Optional[Message]
            If there is already an initial message. Defaults to None.
        Returns
        --------
        :class:`str`
            The signature for the command.
        """
        self.context = context

        resolve_interaction = context.interaction
        kwargs = await self.__get_message_kwargs(resolve_interaction, self._data_source[self.current_page])
        if message is None:
            await super().start(**kwargs)
        else:
            self.message = await message.edit(view=self, **kwargs)

        if wait:
            await self.wait()

    async def __get_kwargs_from_page(self, interaction: Optional[discord.Interaction], data: T) -> Dict[str, Any]:
        formed_page = await discord.utils.maybe_coroutine(self.format_page, interaction, data)
        if isinstance(formed_page, dict):
            return formed_page
        elif isinstance(formed_page, discord.Embed):
            return {"embed": formed_page}
        return {"content": formed_page}

    async def __get_message_kwargs(self, interaction: Optional[discord.Interaction], data: T
                                   ) -> Optional[Dict[str, Any]]:
        return await self.__get_kwargs_from_page(interaction, data)

    async def format_page(self, interaction: Optional[discord.Interaction], data: T
                          ) -> Optional[Union[discord.Embed, Dict[str, Any], str]]:
        """Implementation for each page should be written in this method.

        Parameters
        ------------
        interaction: Optional[Interaction]
            The interaction associated with the view. Can be None when context.interaction is None during the initial
            message send.
        data: T
            The data that will be on each page. This type is based on `data_source`.

        Returns
        --------
        Union[Embed, Dict[str, Any], str]
            The object that will displayed onto the Message. Returning a dictionary is a keyword arguments for the
            `Message.edit`.

        """
        raise NotImplementedError("Format page was not implemented.")

    def disable_buttons_checker(self) -> None:
        """Implementation to disable the buttons every page change."""
        for key in ["start_button", "previous_button"]:
            left_button = self._configuration.get(key)
            if left_button:
                left_button.disabled = not self.current_page

        for key in ["end_button", "next_button"]:
            right_button = self._configuration.get(key)
            if right_button:
                right_button.disabled = self.current_page + 1 >= self.max_pages

    async def change_page(self, interaction: discord.Interaction, page: int) -> None:
        """Implementation to change the page of the View pagination.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is changing the page.
        page: :class: `int`
            The page that the View will switch to.

        """
        previous_page = self.__current_page
        self.__current_page = page
        try:
            self.disable_buttons_checker()
            kwargs = await self.__get_message_kwargs(interaction, self._data_source[page])
            if kwargs is None:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                return

            if interaction.response.is_done():
                await self.message.edit(view=self, **kwargs)
            else:
                await interaction.response.edit_message(view=self, **kwargs)
        except Exception as e:
            self.__current_page = previous_page
            raise e from None

    async def to_start(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the start of the page.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is changing the page.

        """
        await self.change_page(interaction, 0)

    async def to_previous(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the previous page.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is changing the page.

        """
        await self.change_page(interaction, max(self.current_page - 1, 0))

    async def to_stop(self, interaction: discord.Interaction) -> None:
        """Implementation to stop the view.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is stopping the view.

        """
        await interaction.response.defer()
        self.stop()

    async def to_next(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the next page.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is changing the page.

        """
        await self.change_page(interaction, min(self.max_pages - 1, self.current_page + 1))

    async def to_end(self, interaction: discord.Interaction) -> None:
        """Implementation to set the view the end of page.

        Parameters
        ------------
        interaction: Interaction
            The interaction that is changing the page.

        """
        await self.change_page(interaction, self.max_pages - 1)

