from .ui import UIEvent
from ..event_mixins import DataTransferMixin

__all__ = ['InputEvent']


class InputEvent(UIEvent, DataTransferMixin):
    @property
    def data(self) -> str:
        return self.__data__['data']

    @property
    def input_type(self) -> str:
        return self.__data__['inputType']

    @property
    def is_composing(self) -> bool:
        return self.__data__['isComposing']
