from enum import IntEnum

from .ui import UIEvent

__all__ = ['KeyboardEvent', 'KeyLocation']


class KeyLocation(IntEnum):
    # https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent
    DOM_KEY_LOCATION_STANDARD = 0
    DOM_KEY_LOCATION_LEFT = 1
    DOM_KEY_LOCATION_RIGHT = 2
    DOM_KEY_LOCATION_NUMPAD = 3


class KeyboardEvent(UIEvent):
    __interface_for__ = {'keydown', 'keyup'}

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
    def code(self) -> str:
        return self.__data__['code']

    @property
    def is_composing(self) -> bool:
        return self.__data__['isComposing']

    @property
    def key(self) -> str:
        return self.__data__['key']

    @property
    def location(self) -> KeyLocation:
        return KeyLocation(int(self.__data__['location']))

    @property
    def repeat(self) -> bool:
        return self.__data__['repeat']
