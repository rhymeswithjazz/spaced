"""Health check endpoint for container orchestration."""

from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """
    Simple health check endpoint for Docker/Kubernetes.
    Returns 200 if the app is running and database is accessible.
    """
    try:
        # Verify database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy"})
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=503)
