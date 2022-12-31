from __future__ import annotations
import asyncio
from typing import List, Any, TypeVar, Union, Dict, Optional, Generic

import discord
from discord.ext import commands

from ..errors.view import NotViewOwner


__all__ = (
    "SimplePaginationView",
    "ViewAuthor"
)


class ViewAuthor(discord.ui.View):
    """Implementation of View that has an associated owner and handles message sending.

    Parameters
    ------------
    delete_after: :class:`bool`
        Indicate whether to delete the message after it has been stopped or timeout. Defaults to False.
    """
    def __init__(self, *, delete_after: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.delete_after: bool = delete_after
        self.context: Optional[commands.Context] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        """Implements a check whenever interaction is dispatched onto the View.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
           Interaction that triggered the view.

        Raises
        -------
        :class:`NotViewOwner`
            Triggered when the interaction is unauthorized. This is redirected to :meth:`ViewAuthor.on_error`.

        Returns
        --------
        :class:`bool`
            The boolean to allow the interaction to invoke the item callback.

        """
        if interaction.user == getattr(self.context, "author", None):
            return True

        raise NotViewOwner("You cannot interact with this message.")

    async def on_timeout(self) -> None:
        """Implementation for on_timeout that implements after processing calling on_stop."""
        await self.on_stop()

    def stop(self, *, on_stop: bool = True) -> None:
        """Implementation of stop method.

        Parameters
        ------------
        on_stop: :class:`bool`
           Whether to trigger on_stop method for after processing. Defaults to True
        """
        super().stop()
        if on_stop:
            asyncio.create_task(self.on_stop())

    async def on_stop(self):
        """Implements after processing when the view was stopped or on_timeout triggers."""
        if self.message is None:
            return

        if self.delete_after:
            await self.message.delete(delay=0)
            return

        for child in self.children:
            child.disabled = True

        await self.message.edit(view=self)

    async def start(self, context: commands.Context, *args: Any, **kwargs: Any) -> None:
        """Starts the view by sending a message

        This should assign the message that was sent with the view.

        Parameters
        ------------
        context: :class:`~discord.ext.commands.Context`
           The context that will be used to send a message.
        """
        self.context = context
        self.message = await context.send(*args, view=kwargs.pop('view', self), **kwargs)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any], /) -> None:
        """Implementation of on_error if an error occurred during the interaction.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
           Interaction that triggered the view.
        error: :class:`Exception`
            Error that occurred.
        item: :class:`discord.ui.Item`
            The item that is associated during the error occurrance.
        """
        if isinstance(error, NotViewOwner):
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await super().on_error(interaction, error, item)


T = TypeVar('T', bound='SimplePaginationView')

class SimplePaginationView(ViewAuthor):
    """Implementation View pagination that is written purely without any external library.

    This is a simple pagination view without chunking. Chunking of your data should be done before passing into this
    view.

    Parameters
    ------------
    data_source: List[`T`]
       The data source that was paginated before hand.
    delete_after: :class:`bool`
        Indicate whether to delete the message after it has been stopped or timeout. Defaults to False.
    cache_page: :class:`bool`
        Indicate whether to cache the result of format_page for better performance.
        Defaults to False.

    Attributes
    -----------
    context: Optional[:class:`~discord.ext.commands.Context`]
        The context that is associated with this pagination view.
    message: Optional[:class:`discord.Message`]
        The initial message that was sent to the user to be overwritten every interaction.
    """

    def __init__(self, data_source: List[T], /, *, cache_page: bool = False, **kwargs: Any):
        super().__init__(**kwargs)
        self._data_source: List[T] = [*data_source]
        self.__max_pages: int = len(self._data_source)
        self.__current_page: int = 0
        self.__cached_pages: Dict[int, Any] = {}
        self.message: Optional[discord.Message] = None
        self.context: Optional[commands.Context] = None
        self.cache_page: bool = cache_page
        self._configuration: Dict[str, discord.ui.Button] = {}
        self.disable_buttons_checker()

    @property
    def data_source(self) -> List[T]:
        """The data source that is given by the user."""
        return self._data_source.copy()

    async def change_source(self, data_source: List[T], *, interaction: Optional[discord.Interaction] = None, page: int = 0):
        """Change the source of the pagination view. This will edit the view simultaneously.

        Parameters
        -----------
        data_source: List[T]
            The data source that will be set to the view.
        interaction: Optional[:class:`discord.Interaction`]
            The interaction that is involved on changing the source. It uses :meth:`discord.Message.edit` if
            interaction is not provided.
        page: :class:`int`
            The page that will set the paginator to. Defaults to `0`.

        """
        self._data_source = [*data_source]
        self.__max_pages: int = len(self._data_source)
        self.__cached_pages.clear()
        kwargs = await self.show_page(interaction, page)
        if kwargs is None:
            return

        edit = self.message.edit if interaction is None or interaction.response.is_done() else interaction.response.edit_message
        await edit(**kwargs)

    @discord.ui.button(emoji="⏪")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Implementation for the start button that sets the page to the first page."""
        await self.to_start(interaction)

    @discord.ui.button(emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Implementation for the previous button that change the page to the previous page."""
        await self.to_previous(interaction)

    @discord.ui.button(emoji="⏹️")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Implementation for the stop button that stops the view."""
        await self.to_stop(interaction)

    @discord.ui.button(emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Implementation for the next button that change the page to the next page."""
        await self.to_next(interaction)

    @discord.ui.button(emoji="⏩")
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Implementation for the end button that set the page to the end of the page."""
        await self.to_end(interaction)

    @property
    def current_page(self) -> int:
        """The current page of the pagination view."""
        return self.__current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        self.__current_page = value

    @property
    def max_pages(self) -> int:
        """The maximum page of the pagination view that was given."""
        return self.__max_pages

    async def show_page(self, interaction: Optional[discord.Interaction], page: int) -> Optional[Dict[str, Any]]:
        """Calls the :meth:`SimplePaginationView.format_page`.

        Parameters
        ------------
        interaction: Optional[:class:`discord.Interaction`]
            The interaction that will be provided to format_page method.
        page: :class:`int`
            The page that the format_page will set to.

        Returns
        ---------
        Optional[Dict[:class:`str`, Any]]
            Mapping of kwargs that should be given to the :meth:`discord.Message.edit`.
        """
        self.current_page = page
        return await self.get_message_kwargs(interaction, self._data_source[page])

    async def start(self, context: commands.Context, *, wait: bool = False, message: Optional[discord.Message] = None) -> None:
        """Initiate the pagination view by sending the message or editing the message when Message is present.

        Parameters
        ------------
        context:`Context`
            The context associated with the interaction.
        wait: :class:`bool`
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
        kwargs = await self.show_page(resolve_interaction, self.current_page)
        if kwargs is None:
            kwargs = {'view': self}

        if message is None:
            await super().start(context, **kwargs)
        else:
            self.message = await message.edit(**kwargs)

        if wait:
            await self.wait()

    async def __get_kwargs_from_page(self, interaction: Optional[discord.Interaction], data: T) -> Dict[str, Any]:
        formed_page = await discord.utils.maybe_coroutine(self.format_page, interaction, data)
        if isinstance(formed_page, dict):
            return formed_page
        elif isinstance(formed_page, discord.Embed):
            return {"embed": formed_page}
        return {"content": formed_page}

    async def format_view(self, interaction: Optional[discord.Interaction], data: T) -> None:
        """View manipulation should be made on this callback. This is called after format_page finishes invoking.

        Parameters
        ------------
        interaction: Optional[:class:`discord.Interaction`]
            The interaction associated with the view. Can be None when context.interaction is None during the initial
            message send.
        data: T
            The data that will be on each page. This type is based on `data_source`.
        """

    async def resolved_message_kwargs(self, interaction: Optional[discord.Interaction], data: T
                                      ) -> Optional[Dict[str, Any]]:
        """This method handles the cache_page implementation.

        Parameters
        ------------
        interaction: Optional[:class:`discord.Interaction`]
            The interaction associated with the view interaction.
        data: T
            The data that will be on each page. This type is based on `data_source`.

        Returns
        --------
        Optional[Dict[:class:`str`, Any]]
            The kwargs that can be provided on :meth:`discord.Message.edit`. This does not provide you the view key
            argument.
        """
        page = None
        if self.cache_page:
            page = self.__cached_pages.get(self.current_page)

        if not page:
            page = await self.__get_kwargs_from_page(interaction, data)
            if self.cache_page:
                self.__cached_pages[self.current_page] = page

        return page

    async def get_message_kwargs(self, interaction: Optional[discord.Interaction], data: T
                                 ) -> Optional[Dict[str, Any]]:
        kwargs = await self.resolved_message_kwargs(interaction, data)
        self.disable_buttons_checker()
        await discord.utils.maybe_coroutine(self.format_view, interaction, data)
        if kwargs:
            kwargs['view'] = self
        return kwargs

    async def format_page(self, interaction: Optional[discord.Interaction], data: T
                          ) -> Optional[Union[discord.Embed, Dict[str, Any], str]]:
        """Implementation for each page should be written in this method.

        Parameters
        ------------
        interaction: Optional[:class:`discord.Interaction`]
            The interaction associated with the view. Can be None when context.interaction is None during the initial
            message send.
        data: T
            The data that will be on each page. This type is based on `data_source`.

        Returns
        --------
        Union[Embed, Dict[:class:`str`, Any], :class:`str`]
            The object that will displayed onto the Message. Returning a dictionary is a keyword arguments for the
            :meth:`discord.Message.edit`. By default this returns the str of `data` argument.

        """
        return str(data)

    def disable_buttons_checker(self) -> None:
        """Implementation to disable the buttons every page change."""
        for key in ["start_button", "previous_button"]:
            left_button = getattr(self, key, None)
            if left_button:
                left_button.disabled = not self.current_page

        for key in ["end_button", "next_button"]:
            right_button = getattr(self, key, None)
            if right_button:
                right_button.disabled = self.current_page + 1 >= self.max_pages

    async def change_page(self, interaction: discord.Interaction, page: int) -> None:
        """Implementation to change the page of the View pagination.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is changing the page.
        page: :class:`int`
            The page that the View will switch to.

        """
        previous_page = self.current_page
        try:
            kwargs = await self.show_page(interaction, page)
            if kwargs is None:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                return

            if interaction.response.is_done():
                await self.message.edit(**kwargs)
            else:
                await interaction.response.edit_message(**kwargs)
        except Exception as e:
            self.__current_page = previous_page
            raise e from None

    async def to_start(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the start of the page.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is changing the page.

        """
        await self.change_page(interaction, 0)

    async def to_previous(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the previous page.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is changing the page.

        """
        await self.change_page(interaction, max(self.current_page - 1, 0))

    async def to_stop(self, interaction: discord.Interaction) -> None:
        """Implementation to stop the view.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is stopping the view.

        """
        await interaction.response.defer()
        self.stop()

    async def to_next(self, interaction: discord.Interaction) -> None:
        """Implementation to change the page to the next page.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is changing the page.

        """
        await self.change_page(interaction, min(self.max_pages - 1, self.current_page + 1))

    async def to_end(self, interaction: discord.Interaction) -> None:
        """Implementation to set the view the end of page.

        Parameters
        ------------
        interaction: :class:`discord.Interaction`
            The interaction that is changing the page.

        """
        await self.change_page(interaction, self.max_pages - 1)

    @classmethod
    def from_paginator(cls, paginator: commands.Paginator, **kwargs: Any) -> SimplePaginationView:
        """Classmethod to construct pagination view with :class:`~discord.ext.commands.Paginator`.

        .. code-block:: python

            paginator = commands.Paginator()
            paginator.add_line("Page 1\\n Hello!")
            paginator.close_page()
            paginator.add_line("Page 2\\n World!")
            paginator.close_page()
            view = starlight.SimplePaginationView.from_paginator(paginator)
            await view.start(ctx)

        This are constructed normally.

        Parameters
        ------------
        paginator: :class:`~discord.ext.commands.Paginator`
            The paginator that will be used.
        kwargs: Any
            Key arguments that will be passed to :class:`SimplePaginationView`.


        Returns
        --------
        :class:`SimplePaginationView`
            The view paginator constructed.
        """
        return cls(paginator.pages, **kwargs)
