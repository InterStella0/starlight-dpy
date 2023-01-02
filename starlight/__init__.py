from .help_command.command import *
from .help_command.view import *
from .errors.view import *
from .views.pagination import *
from .views.utils import *
from .utils.search import *

from typing import NamedTuple, Literal

__title__ = 'starlight-dpy'
__author__ = 'InterStella0'
__license__ = 'MIT'
__copyright__ = 'Copyright 2022-present InterStella0'
__version__ = '0.0.1a21'


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    level: Literal["a", "b", "o", "f"]
    serial: int


version_info: VersionInfo = VersionInfo(major=0, minor=0, micro=1, level='a', serial=21)
