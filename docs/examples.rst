.. currentmodule:: starlight

Examples
==========
A brief use case of each feature of the library.

You can see a live bot example `here <https://github.com/InterStella0/starlight-dpy/tree/main/examples/live-bot>`_.

Types of HelpCommand
~~~~~~~~~~~~~~~~~~~~

MenuHelpCommand
----------------
Utilizes components to display commands. Uses Select as the general
help command navigation.

.. code-block:: python

    import starlight
    import discord

    from discord.ext import commands

    bot = commands.Bot(
        command_prefix="??",
        help_command=starlight.MenuHelpCommand(
            per_page=10,
            accent_color=0xffcccb,
            error_color=discord.Color.red()
        ),
        intents=discord.Intents.all(),
        description="Demonstration bot"
    )

**Output**

.. image:: /images/default_menu_help.png


PaginateHelpCommand
--------------------
Utilizes components to display commands. Uses Button as the general
help command navigation.

.. code-block:: python

    import starlight
    import discord

    from discord.ext import commands

    bot = commands.Bot(
        command_prefix="??",
        help_command=starlight.PaginateHelpCommand(),
        intents=discord.Intents.all()
    )

**Output**

.. image:: /images/default_paginate_help.png


Views
~~~~~~
There are several implementation of views within the library.

Pagination View
-----------------
A simple pagination interface.

This was designed to not rely on `discord.ext.menus` due to lack of support
for :class:`discord.Interaction`. Majority of code that was present in `discord.ext.menus`
was dedicated for Reaction which has made it not ideal to be inherited.

.. code-block:: python

    import starlight
    import discord

    class MyPagination(starlight.SimplePaginationView):
        async def format_page(self, interaction, data):
            return discord.Embed(
                title=f"Simple display[{self.current_page + 1}/{self.max_pages}]",
                description="\n".join(data)
            )


    @bot.command()
    async def my_command(ctx):
        my_data = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        view = MyPagination(my_data, cache_page=True)
        await view.start(ctx)

**Output**

.. image:: /images/pagination_view.png


Customizing Pagination Button
------------------------------
The base of SimplePaginationView subclasses :class:`discord.ui.View`.
You can override the buttons with the :func:`discord.ui.button` decorator.

Once you override the decorator, you should use the existing method to
apply the navigation behaviour you want.

Available methods to override are as follows:
    * :meth:`SimplePaginationView.start_button` uses :meth:`SimplePaginationView.to_start`
    * :meth:`SimplePaginationView.previous_button` uses :meth:`SimplePaginationView.to_previous`
    * :meth:`SimplePaginationView.stop_button` uses :meth:`SimplePaginationView.to_stop`
    * :meth:`SimplePaginationView.next_button` uses :meth:`SimplePaginationView.to_next`
    * :meth:`SimplePaginationView.end_button` uses :meth:`SimplePaginationView.to_end`


**Example**

.. code-block:: python

    import starlight

    class MyPaginationView(starlight.SimplePaginationView):
        @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
        async def stop_button(self, interaction, button):
            await self.to_stop(interaction)

    # in command
    view = MyPaginationView(['hello', 'my', 'name', 'stella'])
    await view.start(ctx)


Overriding corresponding buttons will completely replace the button. However,
it does retain the position of the button.

.. note::
    By default, :meth:`SimplePaginationView.format_page` returns an str version of your elements.

**Output**

.. image:: /images/customize_pagination_view.png

Inline View
------------
Create inline view for distinct behaviours with `starlight.inline_view`.

.. code-block:: python

    import starlight
    import discord

    @bot.command()
    async def my_command(ctx):
        view = discord.ui.View()
        hi_button = discord.ui.Button(label="hi")
        view.add_item(hi_button)
        await ctx.send("hi", view=view)
        async for interaction, item in starlight.inline_view(view):
            if item is hi_button:
                response = "hi"
            else:
                response = "unknown"
            await interaction.response.send_message(response, ephemeral=True)


You can specify a :class:`discord.ui.Item` to listen for a single item.
Effective when you're expecting only a single interaction.

.. code-block:: python

    result = None
    async for interaction, item in starlight.inline_view(view, item=hi_button):
        result = await view.get_my_result(interaction)
        view.stop()  # ensure only a single sequence

    print("My Result:", result)

.. note::
    Interaction callbacks are sequential due to async iterator.
    You should always go for View subclasses whenever you can.

Inline Pagination
------------------
This is an expanded version of the Inline View concept.
Paginating can have distinct formats which could cause boilerplate code. Which leads to the
creation of Inline Pagination. :class:`InlinePaginationItem` are
yielded for you to respond it to have an effect to the message through
:meth:`InlinePaginationItem.format` method.

.. code-block:: python

    import starlight
    import discord

    @bot.command()
    async def my_command(ctx):
        my_data = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        view = starlight.SimplePaginationView(my_data, cache_page=True)
        async for item in starlight.inline_pagination(view, context=ctx):
            embed = discord.Embed(
                title=f"Simple display[{view.current_page + 1}/{view.max_pages}]",
                description="\n".join(item.data)
            )
            item.format(embed=embed)  # keyword arguments are passed to `Message.edit`

This code output is the equivalent of Pagination View example.

.. note::
    Unlike :meth:`SimplePaginationView.start`, `inline_pagination` is a
    blocking operation. Non-blocking operation can be achieve by wrapping
    :func:`asyncio.create_task` on the async iterator.


General Utility
~~~~~~~~~~~~~~~~
General helper related to discord.py bots.

search
--------
An extended version of :func:`~discord.utils.get()`. However, it is a filter that returns
a sequence. This also supports for fuzzy matching as they are relatively
common to be used within a discord bot.

.. code-block:: python

    from starlight import search, Contains
    # Contains is alias of ContainsFilter class
    items_with_my_value = search(items, my_attr=Contains('my_value'))

    # Equivalent of
    items_contains_value = [item for item in items if 'my_value' in item.my_attr]


convert_help_hybrid
---------------------
Hybrid is a term to implement both text and slash command in
discord.py. HelpCommand was explicitly only a text command. To
change it to a hybrid, you can use :func:`convert_help_hybrid`.

.. code-block:: python

    import discord
    import starlight
    from discord.ext import commands

    GUILD_ID = discord.Object(1010844235857149952)
    my_help_command = commands.DefaultHelpCommand()
    hybrid_help_command = starlight.convert_help_hybrid(my_help_command, guild=GUILD_ID)
    bot = commands.Bot(..., help_command=hybrid_help_command)

Once you sync your command. You can now use help command in slash command.

.. note::
    :func:`convert_help_hybrid` second argument is directly transfered to
    the AppCommand params.
