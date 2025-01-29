from typing import ClassVar, Set

from ...dom import Event

__all__ = ['UIEvent']


class UIEvent(Event):
    __interface_for__: ClassVar[Set[str]] = set()

    @property
    def detail(self) -> int:
        return self.__data__['detail']

    @property
    def layer_x(self) -> int:
        return self.__data__['layerX']

    @property
    def layer_y(self) -> int:
        return self.__data__['layerY']

    @property
    def page_x(self) -> int:
        return self.__data__['pageX']

    @property
    def page_y(self) -> int:
        return self.__data__['pageY']
