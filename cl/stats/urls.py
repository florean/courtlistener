from django.urls import path

from cl.stats.views import (
    celery_fail,
    celery_queue_lengths,
    elasticsearch_status,
    health_check,
    heartbeat,
    redis_writes,
    replication_status,
    sentry_fail,
)

urlpatterns = [
    path(
        "monitoring/celery-queues/",
        celery_queue_lengths,
        name="celery_queue_lengths",
    ),
    path("monitoring/heartbeat/", heartbeat, name="heartbeat"),
    path("monitoring/health-check/", health_check, name="health_check"),
    path("monitoring/redis-writes/", redis_writes, name="check_redis_writes"),
    path(
        "monitoring/elasticsearch-status/",
        elasticsearch_status,
        name="elastic_status",
    ),
    path(
        "monitoring/replication-lag/",
        replication_status,
        name="replication_status",
    ),
    path("sentry/error/", sentry_fail, name="sentry_fail"),
    path("sentry/celery-fail/", celery_fail, name="celery_fail"),
]
