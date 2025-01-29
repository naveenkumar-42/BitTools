from .mouse import MouseEvent

__all__ = ['DragEvent']

from ...event_mixins import DataTransferMixin


class DragEvent(MouseEvent, DataTransferMixin):
    __interface_for__ = {'drag', 'drop',
                         'dragend', 'dragenter', 'dragexit', 'dragleave', 'dragover', 'dragstart'}
