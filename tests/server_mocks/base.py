import traceback
from werkzeug.wrappers import Request
from .utils import RoutePattern, jsonify

class MockedHTTPServer:
    def __init__(self, httpserver):
        self.httpserver = httpserver
        self.base_url = httpserver.url_for("")

    def register_routes(self):
        for attr in dir(self):
            method = getattr(self, attr)
            if hasattr(method, "_route_path"):
                self._bind_handler(method)
        return self

    def _bind_handler(self, handler_func):
        pattern = RoutePattern(handler_func._route_path)
        
        def wrapper(request: Request):
            # Extract {params} from the actual request URI
            kwargs = pattern.extract_params(request.path)
            try:
                return handler_func(request, **kwargs)
            except Exception as e:
                print(f"\nMock Server Error at {request.path}:")
                traceback.print_exc()
                return jsonify({"error": str(e)}, status=500)

        self.httpserver.expect_request(
            uri=pattern, # Using the URIPattern class for binding
            method=handler_func._route_method
        ).respond_with_handler(wrapper)
