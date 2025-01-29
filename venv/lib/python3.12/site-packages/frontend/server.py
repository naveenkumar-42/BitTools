from __future__ import annotations

import inspect
import logging
import uuid
from typing import Any, Callable, Dict, List, TypeVar

import starlette.routing
import uvicorn
from itsdangerous import BadSignature, Signer
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from starlette.staticfiles import StaticFiles

from . import config, utils

__all__ = ['route', 'run']

app: Any = Starlette(debug=config.DEBUG)
app.mount(config.STATIC_ROUTE, StaticFiles(directory=config.STATIC_DIRECTORY), name=config.STATIC_NAME)
app.add_middleware(GZipMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
cookie_signer = Signer(config.SECRET_KEY)

routes: List[Dict[str, Any]] = []

F = TypeVar('F', bound=Callable)


def route(path: str) -> Callable[[F], F]:
    path_regex, path_format, param_converters = starlette.routing.compile_path(path)
    assert path.startswith("/"), "Routed paths must start with '/'"

    def decorator(func: F) -> F:
        routes.append({
            'func': func,
            'path_regex': path_regex,
            'path_format': path_format,
            'param_converters': param_converters,
        })
        return func

    return decorator


# def matches(self, path: str, request: Request) -> Union[bool, Callable]:
#     match = self.path_regex.match(path)
#     if match:
#         matched_params = match.groupdict()
#         for key, value in matched_params.items():
#             matched_params[key] = self.param_convertors[key].convert(value)
#         request.path_params.update(matched_params)
#         return self.func
#     else:
#         return False

@app.route("/resource/{location:path}")
def resource(request: Request) -> Response:
    # todo: move this from webkit to mindwiki
    location = request['path'][9:]
    return FileResponse(location)


@app.route("/{path:path}")
class HTTPService(HTTPEndpoint):
    async def _handle_path(self, request: Request) -> Response:
        route_handler = None
        path = request['path']
        print(path)
        for route in routes:
            match = route['path_regex'].match(path)
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
                request.path_params.update(matched_params)
                route_handler = route['func']
                break
        if route_handler is None:
            return HTMLResponse('404')
        param_count = len(inspect.signature(route_handler).parameters)
        assert param_count < 2, f"Function {route_handler.__name__} cannot have more than one parameter"
        page: WebPage
        if inspect.iscoroutinefunction(route_handler):
            if param_count == 1:
                page = await route_handler(request)
            else:
                page = await route_handler()
        else:
            if param_count == 1:
                page = route_handler(request)
            else:
                page = route_handler()
        assert issubclass(type(page), WebPage), 'Function did not return a web page'
        html = page.__get_html__()
        js: str = utils.make_replacements(dispatcher.dispatcher_js, {
            '%config-host%': config.HOST,
            '%config-port%': config.PORT,
            '%page-id%': id(page),
        })
        html = utils.make_replacements(html, {
            '%dispatcher-js%': js
        })
        return HTMLResponse(html)

    async def get(self, request: Request) -> Response:
        session_cookie = request.cookies.get(config.SESSION_COOKIE_NAME, None)
        new_cookie = False
        if session_cookie is not None:
            try:
                session_id = cookie_signer.unsign(session_cookie).decode("utf-8")
            except BadSignature:
                return PlainTextResponse('Bad Session')
            request.state.session_id = session_id
            request.session_id = session_id
        else:
            # Create new session_id
            request.state.session_id = str(uuid.uuid4().hex)
            request.session_id = request.state.session_id
            new_cookie = True
            logging.debug(f'New session_id created: {request.session_id}')

        response = await self._handle_path(request)

        if new_cookie:
            cookie_value = cookie_signer.sign(request.state.session_id).decode("utf-8")
            response.set_cookie(config.SESSION_COOKIE_NAME, cookie_value, max_age=config.COOKIE_MAX_AGE, httponly=True)
        return response

    # async def on_disconnect(self, page_id) -> JSONResponse:
    #     logging.debug(f'In disconnect Homepage')
    #     await WebPage.instances[page_id].on_disconnect()  # Run the specific page disconnect function
    #     return JSONResponse(False)


def run() -> None:
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level=config.UVICORN_LOGGING_LEVEL)


from .dom import WebPage
from . import dispatcher
