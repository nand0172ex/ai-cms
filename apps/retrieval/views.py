from django.http import JsonResponse


def retrieval_health(request):
	return JsonResponse({"status": "ok", "component": "retrieval"})
