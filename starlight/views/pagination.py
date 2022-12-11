import asyncio
from typing import List, Any, TypeVar, Union, Dict, Optional

import discord
from discord.ext import commands

from ..errors.view import NotViewOwner


__all__ = (
    "SimplePaginationView",
    "ViewEnchanced"
)


T = TypeVar('T')


class ViewEnchanced(discord.ui.View):
    def __init__(self, context: commands.Context, *, delete_after=False, **kwargs):
        super().__init__(**kwargs)
        self.delete_after: bool = delete_after
        self.context: commands.Context = context
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
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

    async def start(self, *args, **kwargs) -> None:
        self.message = await self.context.send(*args, view=self, **kwargs)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any], /) -> None:
        if isinstance(error, NotViewOwner):
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        await super().on_error(interaction, error, item)


class SimplePaginationView(ViewEnchanced):
    start_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏪")
    previous_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="◀️")
    stop_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏹️")
    next_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="▶️")
    end_button: Optional[discord.ui.Button] = discord.ui.Button(emoji="⏩")

    def __init__(self, data_source: List[T], /, *, delete_after: bool = False,
                 message: Optional[discord.Message] = None, **kwargs):
        super().__init__(context=kwargs.pop("context", None), delete_after=delete_after, **kwargs)
        copy_data_source = [*data_source]
        self._data_source: List[T] = copy_data_source
        self.__max_pages: int = len(copy_data_source)
        self.__current_page: int = 0
        self.message: Optional[discord.Message] = message
        self.context: Optional[commands.Context] = None
        self._configuration: Dict[str, discord.ui.Button] = {}
        self._default_configuration()
        self._init_configuration()
        self.disable_buttons_checker()

    def _default_configuration(self):
        valid = {"start_button", "stop_button", "next_button", "end_button", "previous_button"}
        for key, value in SimplePaginationView.__dict__.items():
            instance_value = type(self).__dict__.get(key, discord.utils.MISSING)
            if key in valid:
                if isinstance(instance_value, discord.ui.Button):
                    self._configuration.update({key: instance_value})
                elif instance_value is discord.utils.MISSING:
                    self._configuration.update({key: value})

    def _init_configuration(self):
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

    @property
    def current_page(self) -> int:
        return self.__current_page

    @property
    def max_pages(self) -> int:
        return self.__max_pages

    async def start(self, context: commands.Context, wait: bool = False, *, message: Optional[discord.Message] = None) -> None:
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

    async def __get_message_kwargs(self, interaction: Optional[discord.Interaction], data: T) -> Dict[str, Any]:
        return await self.__get_kwargs_from_page(interaction, data)

    async def format_page(self, interaction: discord.Interaction, data: List[T]) -> Union[discord.Embed, Dict[str, Any], str]:
        raise NotImplementedError("Format page was not implemented.")

    def disable_buttons_checker(self):
        for key in ["start_button", "previous_button"]:
            left_button = self._configuration.get(key)
            if left_button:
                left_button.disabled = not self.current_page

        for key in ["end_button", "next_button"]:
            right_button = self._configuration.get(key)
            if right_button:
                right_button.disabled = self.current_page + 1 >= self.max_pages

    async def change_page(self, interaction: discord.Interaction, page: int) -> None:
        previous_page = self.__current_page
        self.__current_page = page
        try:
            self.disable_buttons_checker()
            kwargs = await self.__get_message_kwargs(interaction, self._data_source[page])
            if interaction.response.is_done():
                await self.message.edit(view=self, **kwargs)
            else:
                await interaction.response.edit_message(view=self, **kwargs)
        except Exception as e:
            self.__current_page = previous_page
            raise e from None

    async def to_start(self, interaction):
        await self.change_page(interaction, 0)

    async def to_previous(self, interaction):
        await self.change_page(interaction, max(self.current_page - 1, 0))

    async def to_stop(self, interaction):
        await interaction.response.defer()
        self.stop()

    async def to_next(self, interaction):
        await self.change_page(interaction, min(self.max_pages - 1, self.current_page + 1))

    async def to_end(self, interaction):
        await self.change_page(interaction, self.max_pages - 1)



