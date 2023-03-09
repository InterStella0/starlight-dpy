.. currentmodule:: starlight

Converters
===========
This section covers all converters that are provided by starlight-dpy.

Extended Command
----------------
Extended Command are commands that adds extra features onto a Command
to have more control on how a command parsing behave.


command
~~~~~~~~
.. autodecorator:: starlight.star_commands.command

hybrid_command
~~~~~~~~~~~~~~
.. autodecorator:: starlight.star_commands.hybrid_command

ExtendedCommand
~~~~~~~~~~~~~~~~
.. autoclass:: starlight.star_commands.ExtendedCommand
    :members:
    :show-inheritance:

ExtendedHybridCommand
~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: starlight.star_commands.ExtendedHybridCommand
    :members:
    :show-inheritance:


Special Converters
------------------
Every converters within this section requires the Extended Command
to be used and function properly.

Separator
~~~~~~~~~~
.. autoclass:: starlight.star_commands.Separator


SeparatorTransform
~~~~~~~~~~~~~~~~~~
.. autoclass:: starlight.star_commands.SeparatorTransform
    :members:

