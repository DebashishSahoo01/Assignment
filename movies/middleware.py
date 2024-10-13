from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class RequestCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if cache.get('request_count') is None:
            cache.set('request_count', 0)

        cache.incr('request_count', 1)

        response = self.get_response(request)
        return response

class RequestCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            request_count = cache.get('request_count', 0)
        except Exception as e:
            return Response({"error": "Failed to retrieve request count"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"requests": request_count}, status=status.HTTP_200_OK)

class ResetRequestCountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cache.set('request_count', 0)
        return Response({"message": "Request count reset successfully"}, status=status.HTTP_204_NO_CONTENT)
