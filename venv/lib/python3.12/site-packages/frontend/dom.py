from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, ClassVar, Coroutine, Dict, final, FrozenSet, Generic, List, Optional, overload, Set, Tuple, Type, TypeVar, Union

from . import config
from .events import *
from .utils import get_all_subclasses, make_replacements

__all__ = ['WebPage', 'Component', 'Event', 'EventPhase', 'EventSlot', 'event_handler']


class EventPhase(IntEnum):
    NONE = 0
    CAPTURING_PHASE = 1
    AT_TARGET = 2
    BUBBLING_PHASE = 3


interface_mapping: Dict[str, Type[Event]] = {}


class Event:
    __interface_for__: ClassVar[Set[str]] = set()

    __data__: Dict[str, Any]

    def __init_subclass__(cls: Type[Event], **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        interface_mapping.update({
            event_name: cls
            for event_name in cls.__interface_for__
        })

    def __init__(self, **kwargs: Any) -> None:
        if '__force_create__' not in kwargs:
            raise TypeError('Cannot instantiate a browser Event')
        self.__data__ = kwargs

    @staticmethod
    def __get_dom_node__(element_id: int) -> Optional[Base]:
        return Base.instances.get(element_id, None)

    @property
    def default_prevented(self) -> bool:
        return self.__data__['defaultPrevented']

    @property
    def event_phase(self) -> EventPhase:
        return EventPhase(self.__data__['eventPhase'])

    @property
    def target(self) -> Optional[Base]:
        return Base.instances.get(int(self.__data__['target']), None)

    @property
    def cancelable(self) -> bool:
        return self.__data__['cancelable']

    @property
    def composed_path(self) -> List[Optional[Base]]:
        return [Base.instances.get(int(item), None) for item in self.__data__['composedPath']]

    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.__data__['timestamp'])

    @property
    def type_(self) -> str:
        return self.__data__['type']


T = TypeVar('T', bound=Event)

Handler = Callable[[T], Union[Optional[bool], Coroutine[Any, Any, Optional[bool]]]]

F = TypeVar('F', bound=Callable)


def event_handler(func: F) -> F:
    return func


class EventSlot(Generic[T]):
    _handler: Optional[Handler] = None
    _component: Component
    _type: str
    _attr_name: str

    def __init__(self, type_: str) -> None:
        self._type = type_

    def __set_name__(self, owner: Type[Component], name: str) -> None:
        self._attr_name = name

    @overload
    def __get__(self, instance: None, owner: Type[Component]) -> Type[EventSlot]:
        ...

    @overload
    def __get__(self, instance: Component, owner: Type[Component]) -> EventSlot:
        ...

    def __get__(self, instance: Optional[Component], owner: Type[Component]) -> Union[Type[EventSlot], EventSlot]:
        if instance is None:
            return self
        listener = instance.__dict__.get(f'__event_{self._type}__', None)
        if listener is None:
            listener = EventSlot(type_=self._type)
            listener._component = instance
            listener._attr_name = self._attr_name
            instance.__dict__[f'__event_{self._type}__'] = listener
        return listener

    def __set__(self, instance: Component, value: Any) -> None:
        raise AttributeError(f'{self._attr_name}: {self._type} is a Browser Event and cannot be assigned to')

    def __delete__(self, instance: Component) -> None:
        raise AttributeError(f'{self._attr_name}: {self._type} is a Browser Event and cannot be deleted')

    @property
    def attr_name(self) -> str:
        return self._attr_name

    @property
    def event_type(self) -> str:
        return self._type

    def set_handler(self, handler: Handler) -> None:
        self._handler = handler
        dispatcher.add_event_listener(page=self._component.page, component=self._component, event_type=self._type)

    def unset_handler(self) -> None:
        self._handler = None
        dispatcher.remove_event_listener(page=self._component.page, component=self._component, event_type=self._type)

    @property
    def handler(self) -> Optional[Handler]:
        return self._handler

    async def __fire__(self, event: T) -> Optional[bool]:
        if self._handler is None:
            return False
        result = self._handler(event)
        if inspect.isawaitable(result):
            return await result  # type: ignore
        else:
            return result  # type: ignore

    def trigger_from_browser(self, event: T) -> None:
        dispatcher.dispatch(page=self._component.page,
                            component=self._component,
                            action='trigger_event',
                            data=dict(type=self._type,
                                      event=event))

    async def trigger(self, event: T) -> None:
        if self._handler is not None:
            await self.__fire__(event=event)


class Base(ABC):
    evt_mouse_click: EventSlot[MouseEvent] = EventSlot('click')
    evt_mouse_double_click: EventSlot[MouseEvent] = EventSlot('dblclick')
    evt_mouse_down: EventSlot[MouseEvent] = EventSlot('mousedown')
    evt_mouse_up: EventSlot[MouseEvent] = EventSlot('mouseup')
    evt_mouse_right_click_context_menu: EventSlot[MouseEvent] = EventSlot('contextmenu')
    evt_mouse_enter: EventSlot[MouseEvent] = EventSlot('mouseenter')
    evt_mouse_leave: EventSlot[MouseEvent] = EventSlot('mouseleave')
    evt_mouse_move: EventSlot[MouseEvent] = EventSlot('mousemove')
    evt_mouse_over: EventSlot[MouseEvent] = EventSlot('mouseover')
    evt_mouse_out: EventSlot[MouseEvent] = EventSlot('mouseout')

    evt_mouse_text_select: EventSlot[UIEvent] = EventSlot('select')
    evt_mouse_wheel_scroll: EventSlot[WheelEvent] = EventSlot('wheel')

    evt_drag: EventSlot[DragEvent] = EventSlot('drag')
    evt_drag_end: EventSlot[DragEvent] = EventSlot('dragend')
    evt_drag_enter: EventSlot[DragEvent] = EventSlot('dragenter')
    evt_drag_start: EventSlot[DragEvent] = EventSlot('dragstart')
    evt_drag_leave: EventSlot[DragEvent] = EventSlot('dragleave')
    evt_drag_over: EventSlot[DragEvent] = EventSlot('dragover')
    evt_drag_drop: EventSlot[DragEvent] = EventSlot('drop')

    evt_input: EventSlot[InputEvent] = EventSlot('input')

    evt_key_press: EventSlot[KeyboardEvent] = EventSlot('keypress')
    evt_key_down: EventSlot[KeyboardEvent] = EventSlot('keydown')
    evt_key_up: EventSlot[KeyboardEvent] = EventSlot('keyup')

    evt_focus_in: EventSlot[FocusEvent] = EventSlot('focusin')
    evt_focus_out_blur: EventSlot[FocusEvent] = EventSlot('focusout')

    # evt_focus: EventSlot[FocusEvent] = EventSlot('focus')  # Not used because these do not bubble
    # evt_blur: EventSlot[FocusEvent] = EventSlot('blur')  # Not used because these do not bubble

    evt_clipboard_cut: EventSlot[ClipboardEvent] = EventSlot('cut')
    evt_clipboard_copy: EventSlot[ClipboardEvent] = EventSlot('copy')
    evt_clipboard_paste: EventSlot[ClipboardEvent] = EventSlot('paste')

    __page__: WebPage
    __parent__: Optional[Union[Component, WebPage]]
    __children__: List[Component]
    __css_classes__: Set[str]
    instances: ClassVar[Dict[int, Union[Component, WebPage]]] = {}

    def __init__(self, *, page: WebPage, attach_to: Optional[Union[WebPage, Component]] = None, **kwargs: Any) -> None:
        self.__children__ = []
        self.__css_classes__ = set()
        Base.instances[id(self)] = self  # type: ignore
        if isinstance(self, WebPage):
            self.__page__ = self
            self.__parent__ = self
        elif isinstance(self, Component):
            self.__page__ = page
            page.__all_component_ids__.add(id(self))
            self.__parent__ = None
            dispatcher.dispatch(page=page, component=self,
                                action='create_component', data=dict(html_tag=self.html_tag,
                                                                     options=kwargs))
        if attach_to is not None and isinstance(self, Component):
            attach_to.insert_child(self)

    def insert_child(self, child: Component, position: Optional[int] = None) -> Union[Component, WebPage]:
        if child.__parent__ is not None:
            child.__parent__.remove_child(child)
        child.__parent__ = self  # type: ignore
        n = len(self.__children__)
        if position is None:
            position = n
        if position < 0:
            position %= n  # make it positive
        position = min(position, n)  # n is allowed, as it means append
        self.__children__.insert(position, child)
        component = None
        if isinstance(self, Component):
            component = self
        dispatcher.dispatch(page=self.page, component=component,
                            action='insert_child', data=dict(child_id=id(child),
                                                             position=position))
        return self  # type: ignore

    def remove_child(self, child: Component) -> Union[Component, WebPage]:
        self.__children__.remove(child)
        child.__parent__ = None
        component = None
        if isinstance(self, Component):
            component = self
        dispatcher.dispatch(page=self.page, component=component,
                            action='remove_child', data=dict(child_id=id(child)))
        return self  # type: ignore

    def replace_inner_html(self, inner_html: str) -> Union[Component, WebPage]:
        if self.children:
            raise ValueError('Can not replace the inner html of a component with managed children')

        component = None
        if isinstance(self, Component):
            component = self

        dispatcher.dispatch(page=self.page, component=component,
                            action='replace_inner_html', data=dict(inner_html=inner_html))
        return self  # type: ignore

    def run_javascript(self, javascript: str, callback: Optional[Callable[..., None]] = None) -> None:
        page: WebPage
        if isinstance(self, WebPage):
            page = self
        elif isinstance(self, Component):
            page = self.page
        else:
            raise TypeError('Must be an instance of Webpage or dom Component')
        dispatcher.dispatch(page=page, component=None,
                            action='run_javascript', data=dict(javascript=javascript),
                            callback=callback)

    async def react(self) -> None:
        await dispatcher.react(self.__page__)

    @property
    def children(self) -> Tuple[Component, ...]:
        return tuple(self.__children__)

    @property
    def page(self) -> WebPage:
        return self.__page__

    @property
    def parent(self) -> Optional[Union[WebPage, Component]]:
        return self.__parent__

    @property
    def pressed_keys(self) -> FrozenSet[config.KEY]:
        if isinstance(self, WebPage):
            return self.__browser_keystate__
        elif isinstance(self, Component):
            return self.__page__.__browser_keystate__
        raise TypeError('Must be an instance of a WebPage or dom Component')

    @final
    async def __run_event__(self, event_type: str, event: Event) -> Optional[bool]:
        for attr in dir(self):
            if attr.startswith('evt_'):
                browser_event = getattr(self, attr)
                if isinstance(browser_event, EventSlot):
                    if browser_event.event_type == event_type:
                        return await browser_event.__fire__(event=event)
        return False

    @abstractmethod
    def delete(self) -> None:
        ...


class WebPage(Base, ABC):
    # language=HTML
    template: ClassVar[str] = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title></title>
        <link rel="shortcut icon" href='/static/favicon2.png'>
        <style>
            %all-component-styles%
        </style>
        %head-html%
    </head>
    <body>
    %body-html%
    <script type="text/javascript">
        %dispatcher-js%
    </script>
    </body>
    </html>
    '''

    # language=HTML
    head_html: ClassVar[str] = ''

    # language=HTML
    body_html: ClassVar[str] = ''

    evt_nav_url_hash_change: EventSlot[HashChangeEvent] = EventSlot('hashchange')
    evt_nav_page_hide = EventSlot('pagehide')
    evt_nav_page_show = EventSlot('pageshow')
    evt_nav_pop_state = EventSlot('popstate')

    evt_before_unload = EventSlot('beforeunload')
    evt_unload = EventSlot('unload')
    evt_load = EventSlot('load')

    evt_online = EventSlot('online')
    evt_offline = EventSlot('offline')

    evt_print_before = EventSlot('beforeprint')
    evt_print_after = EventSlot('afterprint')

    evt_resize = EventSlot('resize')

    __browser_keystate__: FrozenSet[config.KEY]
    __all_component_ids__: Set[int]

    def __init__(self) -> None:
        super().__init__(page=self)
        self.__browser_keystate__ = frozenset()
        self.__all_component_ids__ = set()

    @final
    def __get_html__(self) -> str:
        return make_replacements(self.template, {
            '%all-component-styles%': '\n'.join({cls.css for cls in get_all_subclasses(Base) if issubclass(cls, Component)}),
            '%head-html%': self.head_html,
            '%body-html%': self.body_html,
        })

    def delete(self) -> None:
        for item in list(self.__all_component_ids__):
            try:
                Base.instances[item].delete()
            except:
                pass


TComponent = TypeVar('TComponent', bound='Component')


class Component(Base, ABC):
    html_tag: ClassVar[str] = ''
    # language=CSS
    css: ClassVar[str] = ''

    def __init__(self, page: WebPage, **kwargs: Any) -> None:
        super().__init__(page=page, **kwargs)

    def add_css_classes(self: TComponent, *class_names: str) -> TComponent:
        class_names = tuple(name for class_name in class_names if (name := class_name.strip()))
        if not class_names:
            return self
        for item in class_names:
            self.__css_classes__.add(item)
        dispatcher.dispatch(page=self.page, component=self,
                            action='add_css_classes', data=dict(class_names=class_names))
        return self

    def remove_css_classes(self: TComponent, *class_names: str) -> TComponent:
        class_names = tuple(name for class_name in class_names if (name := class_name.strip()))
        if not class_names:
            return self
        for item in class_names:
            self.__css_classes__.discard(item)
        dispatcher.dispatch(page=self.page, component=self,
                            action='remove_css_classes', data=dict(class_names=class_names))
        return self

    def toggle_css_class(self: TComponent, class_name: str) -> TComponent:
        if class_name in self.__css_classes__:
            return self.remove_css_classes(class_name)
        else:
            return self.add_css_classes(class_name)

    @property
    def css_classes(self) -> Tuple[str, ...]:
        return tuple(self.__css_classes__)

    def delete(self) -> None:
        try:
            self.page.__all_component_ids__.remove(id(self))
            dispatcher.remove_event_listener(page=self.page, component=self)
            dispatcher.dispatch(page=self.page, component=self,
                                action='delete_component')
            del Base.instances[id(self)]
        except KeyError:
            pass


from . import dispatcher
