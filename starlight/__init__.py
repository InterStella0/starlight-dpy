from .star_commands.help_command.command import *
from .star_commands.help_command.view import *
from .star_commands.help_command.injector import *
from .star_commands.errors import *
from .star_commands.views.pagination import *
from .star_commands.views.utils import *
from .utils.general import *
from .utils.search import *

from typing import NamedTuple, Literal

__title__ = 'starlight-dpy'
__author__ = 'InterStella0'
__license__ = 'MIT'
__copyright__ = 'Copyright 2022-present InterStella0'
__version__ = '0.0.1b4'


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    level: Literal["a", "b", "o", "f"]
    serial: int


version_info: VersionInfo = VersionInfo(major=0, minor=0, micro=1, level='b', serial=4)
