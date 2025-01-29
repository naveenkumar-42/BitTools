from .event_mixins import ClipboardDataMixin
from ..dom import Event

__all__ = ['ClipboardEvent']


class ClipboardEvent(Event, ClipboardDataMixin):
    __interface_for__ = {'paste'}
