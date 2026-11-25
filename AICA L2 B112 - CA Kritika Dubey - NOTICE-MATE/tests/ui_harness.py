"""Headless harness that executes frontend/app.py against the REAL backend
services, without a browser, a Streamlit server or a FastAPI server.

* A minimal `streamlit` stand-in records widgets and returns scripted values.
* A minimal `fastapi` stand-in records every route; a fake `requests.request`
  dispatches HTTP calls straight to those route functions (with real pydantic
  validation, real auth tokens and real services/DB).

It catches: Python errors in the UI script, wrong endpoint paths/methods,
request bodies that fail validation, and route handlers that crash.
It cannot check visual layout — that still needs a real browser session.
"""
from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import re
import runpy
import sys
import types
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Rerun(Exception):
    pass


class StopScript(Exception):
    pass


# ---------------------------------------------------------------- fastapi stub
ROUTES: list[tuple[str, re.Pattern, list[str], typing.Callable]] = []


def _install_fastapi_stub():
    fa = types.ModuleType("fastapi")

    def mk(method):
        def deco(path, **k):
            def reg(f):
                names = re.findall(r"{(\w+)}", path)
                pat = re.compile("^" + re.sub(r"{\w+}", r"([^/]+)", path) + "$")
                ROUTES.append((method, pat, names, f))
                return f
            return reg
        return deco

    class APIRouter:
        def __init__(self, *a, **k):
            pass
        get, post, put, delete = staticmethod(mk("GET")), staticmethod(mk("POST")), staticmethod(mk("PUT")), staticmethod(mk("DELETE"))

    class FastAPI:
        def __init__(self, **k):
            self.routers = []

        def add_middleware(self, *a, **k):
            pass

        def middleware(self, *a):
            return lambda f: f

        def exception_handler(self, *a):
            return lambda f: f

        def get(self, *a, **k):
            return lambda f: f

        def include_router(self, r, prefix=""):
            self.routers.append(r)

    fa.APIRouter, fa.FastAPI = APIRouter, FastAPI
    fa.Depends = lambda x=None: None
    fa.File = lambda *a, **k: None
    fa.Header = lambda default=None, **k: default

    class UploadFile:
        pass

    class Request:
        pass

    fa.UploadFile, fa.Request = UploadFile, Request
    resp = types.ModuleType("fastapi.responses")

    class Response:
        def __init__(self, content=None, media_type=None, headers=None, status_code=200):
            self.content, self.media_type, self.headers, self.status_code = content, media_type, headers or {}, status_code

    resp.Response = Response
    resp.JSONResponse = type("JSONResponse", (Response,), {})
    resp.PlainTextResponse = type("PlainTextResponse", (Response,), {})
    exc = types.ModuleType("fastapi.exceptions")
    exc.RequestValidationError = type("RequestValidationError", (Exception,), {})
    mw = types.ModuleType("fastapi.middleware")
    cors = types.ModuleType("fastapi.middleware.cors")
    cors.CORSMiddleware = object
    sys.modules.update({"fastapi": fa, "fastapi.responses": resp, "fastapi.exceptions": exc, "fastapi.middleware": mw,
                        "fastapi.middleware.cors": cors})


# ---------------------------------------------------------------- fake HTTP
class FakeResp:
    def __init__(self, status, body, headers=None):
        self.status_code = status
        self.headers = headers or {}
        if isinstance(body, (bytes, bytearray)):
            self.content, self.text = bytes(body), ""
        elif isinstance(body, str):
            self.content, self.text = body.encode(), body
            self.headers.setdefault("content-type", "text/plain")
        else:
            self.text = json.dumps(body, default=str)
            self.content = self.text.encode()
            self.headers.setdefault("content-type", "application/json")

    def json(self):
        return json.loads(self.text)


CALLS: list[tuple[str, str, int]] = []


def fake_request(method, url, json=None, files=None, params=None, headers=None, timeout=None):  # noqa: A002
    from pydantic import BaseModel, ValidationError as PydErr

    from noticemate.core.errors import NoticeMateError
    from noticemate.services import auth

    path = url.split("/api", 1)[1].split("?")[0]
    for m, pat, names, fn in ROUTES:
        mt = pat.match(path)
        if m != method or not mt:
            continue
        hints = typing.get_type_hints(fn)
        sig = inspect.signature(fn)
        kwargs = {}
        try:
            for pname, prm in sig.parameters.items():
                ann = hints.get(pname)
                if pname == "user":
                    tok = (headers or {}).get("Authorization", "").replace("Bearer ", "")
                    kwargs["user"] = auth.authenticate(tok or None)
                elif pname == "authorization":
                    kwargs[pname] = (headers or {}).get("Authorization")
                elif pname in names:
                    v = mt.group(names.index(pname) + 1)
                    kwargs[pname] = int(v) if ann is int else v
                elif pname == "file":
                    fname, data = files["file"]

                    class UF:
                        filename = fname

                        async def read(self, n):
                            return data[:n]
                    kwargs["file"] = UF()
                elif isinstance(ann, type) and issubclass(ann, BaseModel):
                    kwargs[pname] = ann.model_validate(json or {})
                elif params and pname in params:
                    v = params[pname]
                    kwargs[pname] = (str(v).lower() == "true") if ann is bool else (int(v) if ann is int else v)
            res = fn(**kwargs)
            if asyncio.iscoroutine(res):
                res = asyncio.run(res)
        except NoticeMateError as e:
            CALLS.append((method, path, e.status_code))
            return FakeResp(e.status_code, {"error": e.code, "message": e.message, "details": e.details})
        except PydErr as e:
            CALLS.append((method, path, "SCHEMA"))
            return FakeResp(422, {"error": "validation_error", "message": "Invalid request.", "details": {"errors": str(e)[:500]}})
        CALLS.append((method, path, 200))
        if hasattr(res, "content") and hasattr(res, "media_type"):
            h = {k.lower(): v for k, v in (res.headers or {}).items()}
            h["content-type"] = res.media_type or "application/octet-stream"
            body = res.content if isinstance(res.content, (bytes, bytearray)) else str(res.content)
            if isinstance(body, str) and "text" not in h["content-type"]:
                body = body.encode()
            return FakeResp(200, body, h)
        if isinstance(res, str):
            return FakeResp(200, res, {"content-type": "text/plain"})
        return FakeResp(200, res)
    CALLS.append((method, path, 404))
    raise AssertionError(f"UI called unknown endpoint {method} {path}")


# ---------------------------------------------------------------- streamlit stub
class SessionState(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        self.pop(k, None)


class Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class StStub(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.session_state = SessionState()
        self.script: dict = {}     # label -> value for inputs / True for buttons
        self.rendered: list[str] = []
        self.errors: list[str] = []
        self.sidebar = self

    # layout
    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(n)]

    def tabs(self, labels):
        return [Ctx() for _ in labels]

    def expander(self, *a, **k):
        return Ctx()

    def form(self, *a, **k):
        return Ctx()

    def container(self, *a, **k):
        return Ctx()

    def popover(self, *a, **k):
        return Ctx()

    def spinner(self, *a, **k):
        return Ctx()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    # output
    def _out(self, *a, **k):
        self.rendered.append(" ".join(str(x)[:200] for x in a))

    markdown = caption = title = header = subheader = text = code = json = info = success = warning = _out
    write = dataframe = bar_chart = metric = toast = _out

    def error(self, *a, **k):
        self.errors.append(str(a[0]) if a else "")
        self._out(*a)

    def progress(self, *a, **k):
        return self

    def empty(self, *a, **k):
        return self

    def link_button(self, label, url, **k):
        self.rendered.append(f"LINK:{label}:{url}")
        return False

    def set_page_config(self, **k):
        pass

    def download_button(self, label, data, **k):
        self.rendered.append(f"DOWNLOAD:{label}:{len(data) if data is not None else 0}")

    def file_uploader(self, *a, **k):
        return self.script.get("__files__")

    # inputs
    def _val(self, label, default):
        return self.script.get(label, default)

    def text_input(self, label, value="", **k):
        return self._val(label, value)

    def text_area(self, label, value="", **k):
        return self._val(label, value)

    def number_input(self, label, min_value=None, max_value=None, value=None, **k):
        v = value if value is not None else (min_value if min_value is not None else 0)
        return self._val(label, v)

    def slider(self, label, min_value=0, max_value=100, value=None, **k):
        return self._val(label, value if value is not None else min_value)

    def selectbox(self, label, options, index=0, format_func=str, key=None, **k):
        options = list(options)
        for o in options:
            format_func(o)
        if label in self.script:
            want = self.script[label]
            pick = next((o for o in options if o == want or format_func(o) == want), options[index] if options else None)
            return pick
        return options[index] if options else None

    def radio(self, label, options, index=0, key=None, **k):
        options = list(options)
        if key and key in self.session_state:
            return self.session_state[key]
        v = self._val(label, options[index])
        if key:
            self.session_state[key] = v
        return v

    def multiselect(self, label, options, default=None, **k):
        return self._val(label, list(default or []))

    def checkbox(self, label, value=False, **k):
        return self._val(label, value)

    toggle = checkbox

    def button(self, label, **k):
        return bool(self.script.pop(label, False)) if self.script.get(label) == "once" else bool(self.script.get(label, False))

    form_submit_button = button

    def rerun(self):
        raise Rerun()

    def stop(self):
        raise StopScript()


@contextlib.contextmanager
def harness():
    saved = {k: v for k, v in sys.modules.items() if k == "streamlit" or k.startswith("fastapi") or k.startswith("noticemate.api")}
    for k in list(saved):
        sys.modules.pop(k, None)
    ROUTES.clear()
    _install_fastapi_stub()
    st = StStub()
    sys.modules["streamlit"] = st
    import requests

    real = requests.request
    requests.request = fake_request
    sys.path.insert(0, str(ROOT / "frontend"))
    try:
        import noticemate.api.main  # noqa: F401  registers all routes
        yield st
    finally:
        requests.request = real
        for k in [k for k in sys.modules if k == "streamlit" or k.startswith("fastapi") or k.startswith("noticemate.api") or k in ("ui", "tools")]:
            sys.modules.pop(k, None)
        sys.modules.update(saved)
        if str(ROOT / "frontend") in sys.path:
            sys.path.remove(str(ROOT / "frontend"))


def run(st: StStub, script: dict | None = None, max_reruns: int = 4):
    """Execute app.py once (following st.rerun up to max_reruns)."""
    for _ in range(max_reruns + 1):
        st.script = dict(script or {})
        st.rendered, st.errors = [], []
        try:
            runpy.run_path(str(ROOT / "frontend" / "app.py"), run_name="__main__")
            return
        except Rerun:
            script = {}  # after a rerun, buttons are no longer pressed
            continue
        except StopScript:
            return
