from ..dom import Event

__all__ = ['HashChangeEvent']


class HashChangeEvent(Event):
    __interface_for__ = {'hashchange'}

    @property
    def new_url(self) -> str:
        return self.__data__['newURL']

    @property
    def old_url(self) -> str:
        return self.__data__['oldURL']
