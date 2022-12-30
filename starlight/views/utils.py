from __future__ import annotations
import asyncio
from typing import Optional, Tuple, Any, Dict, TYPE_CHECKING, TypeVar, Union, AsyncIterator, Generic

import discord
from discord.ext import commands
from discord.ui.view import _ViewCallback

if TYPE_CHECKING:
    from starlight.views.pagination import SimplePaginationView

__all__ = (
    "inline_view",
    "InlineView",
    "inline_pagination",
    "InlinePagination",
    "InlinePaginationItem",
)

T = TypeVar("T", bound="InlineIterator")


class InlineIterator(Generic[T]):
    async def next(self) -> Optional[T]:
        raise NotImplementedError("Next was not implemented.")

    def __aiter__(self) -> AsyncIterator[T]:
        return self.aiter()

    async def aiter(self) -> AsyncIterator[T]:
        while True:
            value = await self.next()
            if value is None:
                break

            yield value


_InlineViewReturn = Tuple[discord.Interaction, discord.ui.Item]
class InlineView(InlineIterator[_InlineViewReturn]):
    """Implementation of Inline View concepts.

    Parameters
    -----------
    view: :class:`discord.ui.View`
        The view that will be converted into inline view.
    item: Optional[:class:`discord.ui.Item`]
        The item that should be listen for.
    """
    def __init__(self, view: discord.ui.View, *, item: Optional[discord.ui.Item] = None) -> None:
        self.view: discord.ui.View = view
        self._result: Optional[_InlineViewReturn] = None
        self.__previous_callback: Dict[discord.ui.Item, Any] = {}
        self.__timeout_callback: Any = None
        self.__is_timeout: bool = False
        self.__stop_callback: Any = None
        self.__queue: asyncio.Queue = asyncio.Queue()
        self._plug(item)

    async def _on_timeout(self) -> None:
        self.__is_timeout = True
        self.stop()
        if self.__timeout_callback:
            await self.__timeout_callback()

    def stop(self) -> None:
        """Implementation of stop. This is automatically called once the view was stopped or timeout."""
        self._unplug()
        if not self.__is_timeout and self.__stop_callback:
            self.__stop_callback()

    async def _callback(self, interaction: discord.Interaction, item: discord.ui.Item) -> None:
        await self.__queue.put((interaction, item))

    def _plug(self, item: Optional[discord.ui.Item]) -> None:
        async def callback(_: discord.ui.View, interaction: discord.Interaction, it: discord.ui.Item):
            _callback = self.__previous_callback.get(item)
            if _callback is not None:
                await _callback(interaction)

            await self._callback(interaction, it)

        view = self.view

        for it in [item] if item else view.children:
            self.__previous_callback[it] = it.callback
            it.callback = _ViewCallback(callback, view, it)

        self.__timeout_callback = view.on_timeout
        view.on_timeout = self._on_timeout
        self.__stop_callback = view.stop
        view.stop = self.stop

    def _unplug(self) -> None:
        # cleanup anext
        self.__queue.put_nowait(None)
        self.__queue.task_done()

        for item, callback in self.__previous_callback.items():
            item.callback = callback

        view = self.view
        view.on_timeout = self.__timeout_callback
        view.stop = self.__stop_callback

    async def next(self) -> Optional[_InlineViewReturn]:
        return await self.__queue.get()


inline_view = InlineView

Chunk = TypeVar('Chunk', bound="InlinePaginationItem")

class InlinePaginationItem(Generic[Chunk]):
    """Implementation for inline pagination item.

    This is automatically created by :class:`InlinePagination`. User should not create this.

    Parameters
    -----------
    interaction: :class:`discord.Interaction`
        Interaction that invoked the format_page.
    data: Chunk
        Data chunks that should be displayed onto the user. The type is depended on `data_source`.
    """
    def __init__(self, interaction: discord.Interaction, data: Chunk) -> None:
        self.interaction: discord.Interaction = interaction
        self.data: Chunk = data
        self._future = asyncio.Future()

    def format(self, **kwargs: Any) -> None:
        """A method that signals the paginator on what format should the message show to the user.

        Parameters
        -----------
        kwargs: Any
            Key arguments that will be given to :meth:`discord.Message.edit`. Not passing anything will ignore the
            sequence.
        """
        self._future.set_result(kwargs)

    async def wait(self) -> Dict[str, Any]:
        """Waits for the result to be set on the item.

        Returns
        --------
            Dict[:class:`str`, Any]
            The mapping that was set by the :meth:`InlinePaginationItem.format`.
        """
        return await self._future


class InlinePagination(InlineIterator[InlinePaginationItem]):
    """Async iterator that implements inline pagination view.

    Parameters
    -----------
        pagination_view: :class:`SimplePaginationView`
            The pagination view that will be overwritten.

        context: :class:`commands.Context`
            The context object that will be used to send and manipulate the message.
    """
    def __init__(self, pagination_view: SimplePaginationView, context: commands.Context) -> None:
        self.pagination_view: SimplePaginationView = pagination_view
        self.context = context
        self.__current_waiting_result: Optional[asyncio.Future] = None
        self.__format_page_callback: Any = None
        self.__timeout_callback: Any = None
        self.__is_timeout: bool = False
        self.__stop_callback: Any = None
        self.__queue: asyncio.Queue = asyncio.Queue()
        self.__is_started = False
        self._plug()

    async def _on_timeout(self) -> None:
        self.__is_timeout = True
        self.stop()
        if self.__timeout_callback:
            await self.__timeout_callback()

    def stop(self) -> None:
        """Stops the inline pagination iterator. This will also stop the :attr:`InlinePagination.pagination_view`."""
        self._unplug()
        if not self.__is_timeout and self.__stop_callback:
            self.__stop_callback()

    async def _callback(self, interaction: discord.Interaction, data: T) -> Union[discord.Embed, Dict[str, Any], str]:
        item = InlinePaginationItem(interaction, data)
        await self.__queue.put(item)
        self.__current_waiting_result = item._future
        result = await item.wait()
        self.__current_waiting_result = None
        return result

    def _plug(self) -> None:
        view = self.pagination_view
        self.__format_page_callback = view.format_page
        view.format_page = self._callback

        self.__timeout_callback = view.on_timeout
        view.on_timeout = self._on_timeout
        self.__stop_callback = view.stop
        view.stop = self.stop

    def _unplug(self) -> None:
        # cleanup anext
        self.__queue.put_nowait(None)
        self.__queue.task_done()

        # cleanup callback
        if self.__current_waiting_result and not self.__current_waiting_result.done():
            self.__current_waiting_result.set_result(None)

        view = self.pagination_view
        view.format_page = self.__format_page_callback
        view.on_timeout = self.__timeout_callback
        view.stop = self.__stop_callback

    async def next(self) -> Optional[InlinePaginationItem]:
        if self.__current_waiting_result and not self.__current_waiting_result.done():
            self.__current_waiting_result.set_result(None)  # discard
            self.__current_waiting_result = None

        if not self.__is_started:
            asyncio.create_task(self.pagination_view.start(self.context))
            self.__is_started = True

        return await self.__queue.get()


inline_pagination = InlinePagination
