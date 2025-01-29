from enum import Enum
from typing import List

__all__ = ['ClipboardDataMixin', 'DataTransferMixin']


class ClipboardDataMixin:
    @property
    def text(self) -> str:
        return self.__data__['text']  # type: ignore

    @property
    def images(self) -> List[str]:
        return self.__data__['images']  # type: ignore


class DropEffect(Enum):
    COPY = 'copy'
    MOVE = 'move'
    LINK = 'link'
    NONE = 'none'


class EffectAllowed(Enum):
    NONE = 'none'
    COPY = 'copy'
    COPY_LINK = 'copyLink'
    COPY_MOVE = 'copyMove'
    LINK = 'link'
    LINK_MOVE = 'linkMove'
    MOVE = 'move'
    ALL = 'all'
    UNINITIALIZED = 'uninitialized'


class DataTransferMixin:
    @property
    def drop_effect(self) -> DropEffect:
        return DropEffect(self.__data__['dropEffect'])  # type: ignore

    @property
    def effect_allowed(self) -> EffectAllowed:
        return EffectAllowed(self.__data__['effectAllowed'])  # type: ignore

    @property
    def files(self) -> List[str]:
        return self.__data__['files']  # type: ignore

    @property
    def items(self) -> List[str]:
        return self.__data__['items']  # type: ignore

    @property
    def types(self) -> List[str]:
        return self.__data__['types']  # type: ignore
