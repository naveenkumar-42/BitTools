from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .ui import UIEvent

__all__ = ['FocusEvent']


class FocusEvent(UIEvent):
    __interface_for__ = {'focusin', 'focusout'
                         # 'focus',  # not used because does not bubble
                         # 'blur',  # not used because does not bubble
                         }

    # https://developer.mozilla.org/en-US/docs/Web/API/FocusEvent
    @property
    def related_target(self) -> Optional[dom.Base]:
        return dom.Base.instances.get(int(self.__data__['relatedTarget']), None)


if TYPE_CHECKING:
    from ... import dom
