import uuid


class RequestCorrelationIdMiddleware:
    """Attach correlation ID for request tracing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response
