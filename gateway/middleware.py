"""V2 还没有 Auth。/api/ 的 fetch 不带 CSRF token，先放开。
V3 多端（CLI / 桌面 / 手机局域网）需要 CORS。
"""

from django.http import HttpResponse


class DisableCSRFForAPI:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)


class AllowClientCORS:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
            self._apply(response)
            return response
        response = self.get_response(request)
        self._apply(response)
        return response

    def _apply(self, response) -> None:
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type, X-Client, Authorization"
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response["Access-Control-Max-Age"] = "86400"

