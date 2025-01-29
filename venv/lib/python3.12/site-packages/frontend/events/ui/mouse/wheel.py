from enum import IntEnum

from .mouse import MouseEvent

__all__ = ['DeltaMode', 'WheelEvent']


class DeltaMode(IntEnum):
    DOM_DELTA_PIXEL = 0
    DOM_DELTA_LINE = 1
    DOM_DELTA_PAGE = 2


class WheelEvent(MouseEvent):
    __interface_for__ = {'wheel'}

    @property
    def delta_x(self) -> int:
        return self.__data__['deltaX']

    @property
    def delta_y(self) -> int:
        return self.__data__['deltaY']

    @property
    def delta_z(self) -> int:
        return self.__data__['deltaZ']

    @property
    def delta_mode(self) -> DeltaMode:
        return DeltaMode(int(self.__data__['deltaMode']))
