from __future__ import annotations
import asyncio
from typing import Optional, Tuple, Any, Dict

import discord
from discord.ui.view import _ViewCallback


__all__ = (
    "view_iterator",
    "ViewIterator",
)


class ViewIterator:
    def __init__(self, view: discord.ui.View, *, item: Optional[discord.ui.Item] = None) -> None:
        self.view: discord.ui.View = view
        self._result: Optional[Tuple[discord.Interaction, discord.ui.Item]] = None
        self.__previous_callback: Dict[discord.ui.Item, Any] = {}
        self.__timeout_callback: Any = None
        self.__is_timeout: bool = False
        self.__stop_callback: Any = None
        self.__queue: asyncio.Queue = asyncio.Queue()
        self._plug(item)

    async def on_timeout(self) -> None:
        self.__is_timeout = True
        self.stop()
        if self.__timeout_callback:
            await self.__timeout_callback()

    def stop(self) -> None:
        self._unplug()
        if not self.__is_timeout and self.__stop_callback:
            self.__stop_callback()

    async def callback(self, interaction: discord.Interaction, item: discord.ui.Item) -> None:
        await self.__queue.put((interaction, item))

    def _plug(self, item: Optional[discord.ui.Item]) -> None:
        async def callback(_: discord.ui.View, interaction: discord.Interaction, it: discord.ui.Item):
            await self.callback(interaction, it)

        view = self.view

        for it in [item] if item else view.children:
            self.__previous_callback[it] = it.callback
            it.callback = _ViewCallback(callback, view, it)

        self.__timeout_callback = view.on_timeout
        view.on_timeout = self.on_timeout
        self.__stop_callback = view.stop
        view.stop = self.stop

    def _unplug(self) -> None:
        self.__queue.put_nowait(None)
        self.__queue.task_done()
        for item, callback in self.__previous_callback.items():
            item.callback = callback

        view = self.view
        view.on_timeout = self.__timeout_callback
        view.stop = self.__stop_callback

    def __aiter__(self) -> ViewIterator:
        return self

    async def __anext__(self) -> Tuple[discord.Interaction, discord.ui.Item]:
        value = await self.__queue.get()
        if value is None:
            raise StopAsyncIteration
        return value


view_iterator = ViewIterator
