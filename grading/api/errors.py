from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is None:
        return Response({"error": {"status": 500, "details": "Internal server error"}}, status=500)
    response.data = {"error": {"status": response.status_code, "details": response.data}}
    return response
