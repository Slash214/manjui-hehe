import os

from celery import Celery

# Stage 1 infrastructure only: no generation, TTS or export task is registered.
app = Celery("manju", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
             include=["app.workers.generate", "app.workers.reconcile"])
app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json")
app.conf.update(task_default_queue=os.getenv("GENERATION_QUEUE", "generation"),
                worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=False,
                task_publish_retry=False)
