from __future__ import annotations

from typing import Callable

from .dom import Component

__all__ = ['Div', 'Input']


class Div(Component):
    html_tag = 'div'


class Input(Component):
    html_tag = 'input'

    def get_value(self, callback: Callable) -> None:
        dispatcher.dispatch(page=self.page, component=self,
                            action='get_value', callback=callback)

    def set_value(self, value: str) -> Input:
        dispatcher.dispatch(page=self.page, component=self,
                            action='set_value', data=dict(value=value))
        return self


from . import dispatcher
