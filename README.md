# starlight-dpy
A utility library that she uses for discord.py

This 'library' is still in pre-alpha. Major changes will be made
and the final version is unclear.

Do not use this in a production code.

### Installation
```
pip install git+https://github.com/InterStella0/starlight-dpy
```

## Menu Help Command
Easily paginate your help command with little effort.
```python
import starlight
import discord

from discord.ext import commands

help_command = starlight.MenuHelpCommand(
    per_page=10,
    cog_name="Utility Category",
    accent_color=0xffcccb,
    error_color=discord.Color.red()
)
bot = commands.Bot(
    command_prefix="??", 
    help_command=help_command, 
    intents=discord.Intents.all(),
    description="Demonstration bot"
)
```
**Output**


![default.png](http://api.interstella.online/files/1e6ju4jGXaPYZzbbP1UfHxSq0uDnHQKbf.png)
![pagination.png](http://api.interstella.online//files/1vCH8k3ZTRd4Z7g9ic8OzYJnn1d4uTHTo.png)

### Customizing
You can easily customize your help command by overriding `format_*` methods!
```python
class MyMenuHelpCommand(starlight.MenuHelpCommand):
    def __init__(self):
        super().__init__(cog_name="Utility Category", accent_color=0xffcccb)

    async def format_front_bot_menu(self, mapping):
        return discord.Embed(
            title="Help",
            description="Choose a category to display your help command!",
            color=self.accent_color
        )


help_command = MyMenuHelpCommand()
bot = commands.Bot(command_prefix="??", help_command=help_command, intents=discord.Intents.all())
```
**Output**
![output.png](http://api.interstella.online/files/1OMN59oaNjq-DxM9_upOTSRHNujO5R6mk.png)
