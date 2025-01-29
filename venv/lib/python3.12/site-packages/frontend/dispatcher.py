from __future__ import annotations

import functools
import itertools
import json
import logging
import traceback
from collections import defaultdict
from copy import deepcopy
from typing import Any, Callable, cast, DefaultDict, Dict, List, Optional, Set, TypeVar, Union

from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from . import config, server
from .async_utils import later_await

__all__ = ['react']

__callback_id__ = itertools.count(0)
callbacks: Dict[int, Callable] = {}
socket_id_to_socket: Dict[int, WebSocket] = {}
socket_id_to_page: Dict[int, dom.WebPage] = {}
page_to_socket: Dict[dom.WebPage, WebSocket] = {}
to_dispatch: DefaultDict[dom.WebPage, List[Dict[str, Any]]] = defaultdict(list)
event_listeners: DefaultDict[dom.WebPage, DefaultDict[str, Set[dom.Component]]] = defaultdict(lambda: defaultdict(set))

F = TypeVar('F', bound=Callable)


def with_traceback(func: F) -> F:
    @functools.wraps(func)
    def inner(*args: Any, **kwargs: Any) -> Any:
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logging.error('%s %s', 'Error:', '\u001b[47;1m\033[93m:' + str(e) + '\033[0m')
            traceback.print_exc()

    return cast(F, inner)


##############################################################################################################
##                                    V I E W   ->   D I S P A T C H E R                                    ##
##############################################################################################################


def add_event_listener(page: dom.WebPage, component: dom.Component, event_type: str) -> None:
    event_listeners[page][event_type].add(component)
    dispatch(page=page, component=None,
             action='add_event_listener',
             data={
                 'event_type': event_type,
             })


def remove_event_listener(page: dom.WebPage, component: dom.Component, event_type: Optional[str] = None) -> None:
    if event_type is None:
        for event_type in event_listeners[page]:
            remove_event_listener(page, component, event_type)
    else:
        event_listeners[page][event_type].discard(component)
        if not event_listeners[page][event_type]:
            dispatch(page=page, component=None,
                     action='remove_event_listener',
                     data={
                         'event_type': event_type
                     })


def dispatch(page: dom.WebPage,
             action: str,
             component: Optional[dom.Component] = None,
             data: Optional[Dict[str, Any]] = None,
             callback: Optional[Callable] = None) -> None:
    callback_id = None
    if callback is not None:
        callback_id = next(__callback_id__)
        callbacks[callback_id] = callback
    to_dispatch[page].append({
        'component_id': id(component) if component is not None else None,
        'action': action,
        'data': data,
        'callback_id': callback_id
    })


##############################################################################################################
##                                 D I S P A T C H E R   ->   B R O W S E R                                 ##
##############################################################################################################


async def react(page: dom.WebPage) -> None:
    if not to_dispatch[page]:
        return
    websocket = page_to_socket[page]
    message = deepcopy(to_dispatch[page])
    to_dispatch[page].clear()
    later_await(websocket.send_json(message), 0)


##############################################################################################################
##                                 B R O W S E R   ->   D I S P A T C H E R                                 ##
##############################################################################################################


@server.app.websocket_route("/")
class EventService(WebSocketEndpoint):
    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        logging.debug(f'Websocket {id(websocket)} connected')

    async def on_receive(self, websocket: WebSocket, message: str) -> None:
        logging.debug('%s %s', f'Socket ({id(websocket)}) {websocket}: message received:', message)
        page: dom.WebPage = socket_id_to_page.get(id(websocket), None)  # type: ignore
        for json_data in json.loads(message):
            try:
                action, data = json_data['action'], json_data['data']
                if action == 'connect':
                    page = cast(dom.WebPage, dom.Base.instances[int(data['page_id'])])
                    page_to_socket[page] = websocket
                    socket_id_to_page[id(websocket)] = page
                    socket_id_to_socket[id(websocket)] = websocket
                    continue
                page.__browser_keystate__ = frozenset(config.KEY(item) for item in json_data['down_keys'].keys())
                if action == 'event':
                    later_await(run_event(data, page), 0)
                elif action == 'run_callback':
                    later_await(run_callback(data['callback_id'], **data['result']), 0)
            except Exception as e:
                logging.error('%s %s', 'Event result:', '\u001b[47;1m\033[93mAttempting to run event handler:' + str(e) + '\033[0m')
                traceback.print_exc()
        later_await(react(page), 0)

    async def on_disconnect(self, websocket: WebSocket, close_code: Any) -> None:
        page: dom.WebPage = socket_id_to_page[id(websocket)]
        page.delete()
        del page_to_socket[page]
        del socket_id_to_socket[id(websocket)]
        del socket_id_to_page[id(websocket)]
        del to_dispatch[page]


##############################################################################################################
##                                    D I S P A T C H E R   ->   V I E W                                    ##
##############################################################################################################


@with_traceback
async def run_event(data: Dict[str, Any], page: dom.WebPage) -> None:
    event_type = data['event']['type']
    event = dom.interface_mapping[event_type](__force_create__=True, **data['event'])
    component_id = data['component_id']
    if component_id is None:
        target = page
    else:
        target = cast(dom.WebPage, dom.Base.instances.get(int(component_id), None))
    if target is not None:
        path = []
        component: Union[dom.WebPage, dom.Component] = target
        while component.parent is not None and component.parent != component:
            component = component.parent
            path.append(component)
        phased_path = [(component, dom.EventPhase.CAPTURING_PHASE) for component in reversed(path)]
        phased_path += [(target, dom.EventPhase.AT_TARGET)]
        phased_path += [(component, dom.EventPhase.BUBBLING_PHASE) for component in path]
        for component, phase in phased_path:
            event.__data__['eventPhase'] = phase
            stop_propagation = await component.__run_event__(event_type=event_type,
                                                             event=event)
            if stop_propagation is True:
                break


@with_traceback
async def run_callback(callback_id: int, **result: Any) -> None:
    if (callback := callbacks.get(callback_id, None)) is not None:
        callback(**result)
        # todo: support async callbacks
        del callbacks[callback_id]


##############################################################################################################
##                                              B R O W S E R                                               ##
##############################################################################################################

# language=JavaScript
dispatcher_js: str = '''// dispatcher-code
window.socket = new WebSocket("ws://%config-host%:%config-port%/");
window.down_keys = {};
window.page_id = '%page-id%';
window.elements = {};
window.to_dispatch = [];

document.addEventListener('keydown', ev => {
    window.down_keys[ev.code] = true;
});

document.addEventListener('keyup', ev => {
    delete window.down_keys[ev.code];
});

document.addEventListener('blur', ev => {
    window.down_keys = {};
});

function flush_events() {
    if (window.to_dispatch.length === 0) return;
    window.socket.send(JSON.stringify(window.to_dispatch));
    window.to_dispatch = [];
}

window.socket.onopen = function (event) {
    dispatch({
        action: 'connect',
        data: {
            page_id: '%page-id%'
        }
    });
    flush_events();
};

function dispatch(event) {
    event.down_keys = JSON.parse(JSON.stringify(window.down_keys));
    window.to_dispatch.push(event);
}

window.socket.onmessage = function (event) {
    let commands = JSON.parse(event.data);
    for (let i = 0; i < commands.length; i++) {
        let command = commands[i];
        let result = null;
        let component_id = command.component_id;
        let action = command.action;
        let data = command.data;
        let callback_id = command.callback_id;

        switch (action) {
            case 'create_component':
                let element = document.createElement(data.html_tag, data.options);
                element.setAttribute('id', component_id);
                window.elements[component_id] = element;
                break;
            case 'delete_component':
                let elem = window.elements[component_id];
                delete window.elements[component_id];
                elem.remove();
                break;
            case 'insert_child':
                if (data.position === null || data.position === undefined)
                    data.position = 0;
                let parent = (component_id !== null && component_id !== undefined) ? window.elements[component_id] : document.body;
                let child = window.elements[data.child_id];
                if (data.position >= parent.children.length)
                    parent.appendChild(child);
                else
                    parent.insertBefore(child, parent.children[data.position]);
                break;
            case 'remove_child':
                window.elements[component_id].removeChild(window.elements[data.child_id]);
                break;
            case 'replace_inner_html':
                window.elements[component_id].innerHTML = data.inner_html;
                break;
            case 'get_inner_html':
                result = window.elements[component_id].innerHTML;
                break;
            case 'get_value':
                result = window.elements[component_id].value;
                break;
            case 'set_value':
                window.elements[component_id].value = data.value;
                break;
            case 'run_javascript':
                result = eval(data.javascript);
                break;
            case 'add_css_classes':
                for (let j = 0; j < data.class_names.length; j++) {
                    window.elements[component_id].classList.add(data.class_names[j]);
                }
                break;
            case 'remove_css_classes':
                for (let j = 0; j < data.class_names.length; j++) {
                    window.elements[component_id].classList.remove(data.class_names[j]);
                }
                break;
            case 'add_event_listener':
                document.body.addEventListener(data.event_type, event_listener);
                break;
            case 'remove_event_listener':
                document.body.removeEventListener(data.event_type, event_listener);
                break;
            case 'trigger_event':
                window.elements[component_id].dispatchEvent(
                    new Event(data.type, data.event)
                );
                break;
        }
        if (callback_id !== null && callback_id !== undefined)
            dispatch({
                action: 'run_callback',
                data: {
                    callback_id: callback_id,
                    result: result,
                },
            });
    }
    flush_events();
};

window.socket.onclose = function (event) {
    console.log(event.data);
};

window.socket.onerror = function (error) {
    console.log(error);
};

function jsonify_event(e) {
    const obj = {};
    for (let k in e) {
        obj[k] = e[k];
    }
    return JSON.parse(JSON.stringify(obj, (k, v) => {
        if (v instanceof Node) return 'node-' + v.id;
        if (v instanceof Window) return 'window';
        return v;
    }, ' '));
}

async function fileListToBase64(fileList) {
    function getBase64(file) {
        const reader = new FileReader()
        return new Promise(resolve => {
            reader.onload = ev => {
                resolve(ev.target.result)
            }
            reader.readAsDataURL(file)
        })
    }

    const promises = []
    for (let i = 0; i < fileList.length; i++) {
        promises.push(getBase64(fileList[i]))
    }
    return await Promise.all(promises)
}

async function event_listener(event) {
    if (event.clipboardData !== undefined && event.clipboardData !== null) {
        event.text = event.clipboardData.getData('text/plain');
        var items = (event.clipboardData || event.originalEvent.clipboardData).items;
        var blobs = [];
        for (index in items) {
            let item = items[index];
            if (item.kind === 'file') {
                blobs.push(item.getAsFile());
            }
        }
        event.images = await fileListToBase64(blobs);
    }
    if (event.dataTransfer !== undefined && event.dataTransfer !== null) {
        event.dropEffect = event.dataTransfer.dropEffect;
        event.effectAllowed = event.dataTransfer.effectAllowed;
        event.files = event.dataTransfer.files;
        event.types = event.dataTransfer.types;
        event.items = event.dataTransfer.items;
    }
    let target = event.target;
    let target_id = null;
    while (target !== null && (target.id === null || target.id === undefined || window.elements[target.id] === undefined || window.elements[target.id] === null)) {
        target = target.parentElement;
    }
    if (target !== null)
        target_id = target.id;
    event = jsonify_event(event);
    dispatch({
        action: 'event',
        data: {
            component_id: target_id,
            event: event,
        },
    });
    flush_events();
}
'''

from . import dom
