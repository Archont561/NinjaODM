import json
import re
from pytest_httpserver import URIPattern
from werkzeug.wrappers import Response


def jsonify(data: dict, status: int = 200) -> Response:
    """
    Converts a python dictionary to a JSON HTTP Response.
    """
    return Response(json.dumps(data), mimetype="application/json", status=status)


def route(path, method="GET"):
    """FastAPI-style route decorator: @route('/task/{uuid}/info')"""

    def decorator(func):
        func._route_path = path
        func._route_method = method
        return func

    return decorator


class RoutePattern(URIPattern):
    """Integrates FastAPI-style paths into pytest-httpserver matching."""

    def __init__(self, path_template):
        self.path_template = path_template
        # Convert /task/{uuid}/info -> ^/task/(?P<uuid>[^/]+)/info$
        escaped = re.escape(path_template).replace(r"\{", "{").replace(r"\}", "}")
        regex_str = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", escaped)
        self.regex = re.compile(f"^{regex_str}$")

    def match(self, uri: str) -> bool:
        return bool(self.regex.match(uri))

    def extract_params(self, uri: str) -> dict:
        match = self.regex.match(uri)
        return match.groupdict() if match else {}
