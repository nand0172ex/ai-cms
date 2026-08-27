from celery import shared_task

from apps.connectors.models import ConnectorConfig
from apps.connectors.services import ConnectorSyncService


@shared_task
def sync_connector(connector_id):
    connector = ConnectorConfig.objects.get(id=connector_id)
    return ConnectorSyncService().run_sync(connector).id


@shared_task
def sync_all_active_connectors():
    ids = []
    for connector in ConnectorConfig.objects.filter(is_active=True):
        ids.append(ConnectorSyncService().run_sync(connector, force=False).id)
    return ids
