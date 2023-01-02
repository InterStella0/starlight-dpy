from collections import namedtuple
from typing import Optional, Sequence

import discord
from discord.ext import commands

import starlight
from starlight.utils.search import Fuzzy

from utils.pagination import StellaPagination


class MyHelpCommand(starlight.MenuHelpCommand):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.view_provider = MyViewProvider(self)
        dummy_paginators = StellaPagination([])
        self.pagination_buttons = {
            'start_button': discord.ui.Button(emoji=dummy_paginators.start_button.emoji, row=1),
            'previous_button': discord.ui.Button(emoji=dummy_paginators.previous_button.emoji, row=1),
            'stop_button': discord.ui.Button(emoji=dummy_paginators.stop_button.emoji, row=1),
            'next_button': discord.ui.Button(emoji=dummy_paginators.next_button.emoji, row=1),
            'end_button': discord.ui.Button(emoji=dummy_paginators.end_button.emoji, row=1),
        }
        self.cls_home_button = MyHomeButton

    async def command_callback(self, ctx, /, *, command: Optional[str] = None) -> None:
        if command:  # implement searching for '??help <command>'
            cmd_or_cog = ctx.bot.get_command(command) or ctx.bot.get_cog(command)
            if not cmd_or_cog:
                await self.command_search(command)
                return

        await super().command_callback(ctx, command=command)

    async def command_search(self, command: str):
        bot = self.context.bot
        CommandAliases = namedtuple("CommandAliases", "all_names")
        cmd_names = [CommandAliases([c.qualified_name, *c.aliases]) for c in  bot.all_commands.values()]
        found_cmd_names = starlight.search(cmd_names, sort=True, all_names=FuzzyContainsFilter(command))
        found_cmds = [bot.get_command(x.all_names[0]) for x in found_cmd_names]
        found_cmds = [x for x in dict.fromkeys(found_cmds)]  # unique commands
        if not found_cmds:
            raise commands.BadArgument(f"No command found for {command}")

        data = discord.utils.as_chunks(found_cmds, 5)
        view = StellaPagination(data, cache_page=True)
        inline = starlight.inline_pagination(view, self.context)
        async for item in inline:
            embed = discord.Embed(title=f"List of command similar to '{command}'", color=self.accent_color)
            for cmd in item.data:
                docs = f"**Description: **{cmd.short_doc}"
                if cmd.aliases:
                    docs = f"**Aliases: **{', '.join(cmd.aliases)}\n" + docs
                embed.add_field(name=self.get_command_signature(cmd), value=docs, inline=False)

            no_cmd = "No command found for `{}`. Here is the result for similar to it."
            content = no_cmd.format(command) if not view.current_page else None
            item.format(content=content, embed=embed)

    async def format_bot_page(self, view, mapping):
        embed = await super().format_bot_page(view, mapping)
        for i, field in enumerate(embed.fields):
            cog_name, _, cmd_amount = field.name.rpartition(' ')
            mapper = [x for x in mapping if x]
            cog = discord.utils.get(mapper, qualified_name=cog_name)
            emoji = getattr(cog, "emoji", '⚠️')
            embed.set_field_at(i, name=f'{emoji} {field.name}', value=field.value, inline=field.inline)

        return embed


class MyDropdown(starlight.MenuDropDown):
    def create_category_option(self, cog):
        option = super().create_category_option(cog)
        option.emoji = getattr(cog, "emoji", '⚠️')
        return option


class MyHelpMenuBot(starlight.HelpMenuBot):
    def generate_dropdown(self, cogs, **kwargs):
        return MyDropdown(no_category=self.no_category, placeholder="Select a category...", **kwargs)


class MyViewProvider(starlight.HelpMenuProvider):
    async def provide_bot_view(self, mapping):
        help_command = self.help_command
        return MyHelpMenuBot(
            help_command, mapping
        )

class MyHomeButton(starlight.MenuHomeButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = '🏘️'


class FuzzyContainsFilter(Fuzzy):
    """This custom filter searches the entire sequence if there is a higher ratio value within an attribute."""
    def filter(self, value: Sequence, /) -> float:
        return max(self.get_ratio(self.query, x) for x in value)
