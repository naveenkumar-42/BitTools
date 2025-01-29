from __future__ import annotations

from enum import IntEnum
from typing import List, Optional, TYPE_CHECKING

from ..ui import UIEvent

__all__ = ['MouseEvent', 'MouseButton']


class MouseButton(IntEnum):
    MAIN_LEFT = 0
    AUXILIARY_WHEEL_MIDDLE = 1
    SECONDARY_RIGHT = 2
    FOURTH_BROWSERBACK = 3
    FOURTH_BROWSERFORWARD = 4


class MouseEvent(UIEvent):
    __interface_for__ = {'click', 'dblclick', 'mouseup', 'mousedown'}

    @property
    def alt_key(self) -> bool:
        return self.__data__['altKey']

    @property
    def ctrl_key(self) -> bool:
        return self.__data__['ctrlKey']

    @property
    def meta_key(self) -> bool:
        return self.__data__['metaKey']

    @property
    def shift_key(self) -> bool:
        return self.__data__['shiftKey']

    @property
    def button(self) -> MouseButton:
        return MouseButton(self.__data__['button'])

    @property
    def buttons(self) -> List[MouseButton]:
        return [MouseButton(item) for item in self.__data__['buttons']]

    @property
    def client_x(self) -> int:
        return self.__data__['clientX']

    @property
    def client_y(self) -> int:
        return self.__data__['clientY']

    @property
    def movement_x(self) -> int:
        return self.__data__['movementX']

    @property
    def movement_y(self) -> int:
        return self.__data__['movementY']

    @property
    def offset_x(self) -> int:
        return self.__data__['offsetX']

    @property
    def offset_y(self) -> int:
        return self.__data__['offsetY']

    @property
    def screen_x(self) -> int:
        return self.__data__['screenX']

    @property
    def screen_y(self) -> int:
        return self.__data__['screenY']

    @property
    def x(self) -> int:
        return self.__data__['x']

    @property
    def y(self) -> int:
        return self.__data__['y']

    @property
    def region(self) -> int:
        return self.__data__['region']

    @property
    def related_target(self) -> Optional[dom.Base]:
        return super().__get_dom_node__(int(self.__data__['relatedTarget']))


if TYPE_CHECKING:
    from .... import dom
