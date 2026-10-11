print('init deep', __name__, __package__)
from . import SUB_CONST
from .. import pkg_func
from ..beta import BETA
from . import sibling
from .sibling import SIB as S2
DEEP = (SUB_CONST, pkg_func(), BETA, sibling.SIB, S2)
