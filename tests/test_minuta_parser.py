import importlib
import os
import sys
import types


def prepare_stubs():
    flask_stub = types.ModuleType("flask")
    class DummyFlask:
        def __init__(self, *a, **k):
            self.config = {}
            self.secret_key = None
        def route(self, *a, **k):
            def decorator(f):
                return f
            return decorator
        def errorhandler(self, *a, **k):
            def decorator(f):
                return f
            return decorator
    flask_stub.Flask = DummyFlask
    flask_stub.request = types.SimpleNamespace()
    flask_stub.jsonify = lambda *a, **k: None
    flask_stub.session = {}
    flask_stub.redirect = lambda *a, **k: None
    flask_stub.url_for = lambda *a, **k: ""
    flask_stub.make_response = lambda x: x
    flask_stub.g = types.SimpleNamespace()
    sys.modules.setdefault("flask", flask_stub)

    flask_session_stub = types.ModuleType("flask_session")
    flask_session_stub.Session = lambda *a, **k: None
    sys.modules.setdefault("flask_session", flask_session_stub)

    flask_cors_stub = types.ModuleType("flask_cors")
    flask_cors_stub.CORS = lambda *a, **k: None
    sys.modules.setdefault("flask_cors", flask_cors_stub)

    werk_utils = types.ModuleType("werkzeug.utils")
    werk_utils.secure_filename = lambda name: name
    sys.modules.setdefault("werkzeug.utils", werk_utils)
    werk_stub = types.ModuleType("werkzeug")
    werk_stub.utils = werk_utils
    sys.modules.setdefault("werkzeug", werk_stub)

    fitz_stub = types.ModuleType("fitz")
    fitz_stub.open = lambda *a, **k: types.SimpleNamespace(__iter__=lambda self: iter([]), close=lambda: None)
    sys.modules.setdefault("fitz", fitz_stub)

    markupsafe_stub = types.ModuleType("markupsafe")
    markupsafe_stub.escape = lambda x: x
    sys.modules.setdefault("markupsafe", markupsafe_stub)


def import_backend_module():
    prepare_stubs()
    genai_stub = types.SimpleNamespace(
        configure=lambda **kwargs: None,
        GenerativeModel=lambda *args, **kwargs: object(),
        types=types.SimpleNamespace(GenerationConfig=object),
    )
    google_stub = types.ModuleType("google")
    google_stub.generativeai = genai_stub
    sys.modules.setdefault("google", google_stub)
    sys.modules.setdefault("google.generativeai", genai_stub)
    os.environ.setdefault("GEMINI_API_KEY", "dummy")
    return importlib.import_module("backend.contestacao")


def test_parse_minuta_to_single_block():
    module = import_backend_module()
    result = module.MinutaParser.parse_minuta_to_single_block("texto da minuta")
    assert result == {"CONTESTAÇÃO COMPLETA": "texto da minuta"}
