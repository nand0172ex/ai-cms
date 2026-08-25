from django.db import connections
from django.http import JsonResponse

from apps.audit.models import AuditEvent
from apps.conversations.models import Message
from apps.ingestion.models import IngestionJob


def health(request):
	return JsonResponse({"status": "ok"})


def ready(request):
	db_ok = True
	try:
		with connections["default"].cursor() as cursor:
			cursor.execute("SELECT 1")
			cursor.fetchone()
	except Exception:
		db_ok = False

	if db_ok:
		return JsonResponse({"status": "ready", "database": "ok"})
	return JsonResponse({"status": "not_ready", "database": "error"}, status=503)


def metrics(request):
	return JsonResponse(
		{
			"messages_total": Message.objects.count(),
			"ingestion_jobs_total": IngestionJob.objects.count(),
			"audit_events_total": AuditEvent.objects.count(),
		}
	)
