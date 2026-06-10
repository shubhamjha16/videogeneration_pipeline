"""
RabbitMQ Consumer — EaseToLearn Video Factory

Subscribes to the etl.video.render.queue and processes render jobs
dispatched by the Spring Boot integration service (or the Python replacement).

Architecture:
    Publisher sends RenderRequest JSON → RabbitMQ → This consumer
    → Deserializes JSON → Registers job in api_bridge.jobs + DB
    → Launches pipeline in worker thread → ACKs message immediately
    → On deserialization/registration failure → NACKs (routes to DLQ)

Heartbeat safety:
    Pipeline runs in a separate thread so the Pika callback returns
    quickly.  This prevents heartbeat starvation on multi-minute renders
    that would otherwise cause the broker to drop the connection, fail the
    ACK, and redeliver the message (duplicate render).

Graceful degradation:
    If RABBITMQ_URL is not set, the consumer silently skips startup
    and the factory falls back to direct HTTP /render endpoint mode.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("video_factory.mq")

# ── Queue topology (mirrors RabbitMQConfig.java) ───────────────────────────
EXCHANGE         = "etl.video.exchange"
RENDER_QUEUE     = "etl.video.render.queue"
DEAD_LETTER_QUEUE = "etl.video.render.dlq"
RENDER_ROUTING_KEY = "video.render"
DLX              = "etl.video.dlx"
DLQ_ROUTING_KEY  = "video.render.dead"


def _get_rabbitmq_url() -> Optional[str]:
    """Resolve AMQP URL from environment."""
    url = os.environ.get("RABBITMQ_URL", "")
    if url:
        return url

    # Construct from individual components (matches application.yml defaults)
    host = os.environ.get("RABBITMQ_HOST", "")
    if host:
        user    = os.environ.get("RABBITMQ_USER", "guest")
        passwd  = os.environ.get("RABBITMQ_PASS", "guest")
        port    = os.environ.get("RABBITMQ_PORT", "5672")
        vhost   = os.environ.get("RABBITMQ_VHOST", "%2F")  # URL-encoded "/"
        return f"amqp://{user}:{passwd}@{host}:{port}/{vhost}"

    return None


def _ensure_topology(channel):
    """
    Idempotently declare the exchange, main queue, DLX, and DLQ.
    Safe to call on every connection — RabbitMQ ignores re-declarations
    when attributes match.
    """
    # Main exchange
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="direct",
        durable=True,
    )

    # Dead-letter exchange
    channel.exchange_declare(
        exchange=DLX,
        exchange_type="direct",
        durable=True,
    )

    # Main render queue (routes failures to DLX)
    channel.queue_declare(
        queue=RENDER_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange":    DLX,
            "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
        },
    )

    # Dead letter queue
    channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)

    # Bindings
    channel.queue_bind(RENDER_QUEUE, EXCHANGE, RENDER_ROUTING_KEY)
    channel.queue_bind(DEAD_LETTER_QUEUE, DLX, DLQ_ROUTING_KEY)

    # Process one job at a time per worker (backpressure control)
    channel.basic_qos(prefetch_count=1)

    logger.info("✅ MQ topology verified: exchange=%s queue=%s", EXCHANGE, RENDER_QUEUE)


def _register_mq_job(job_id: str, topic: str, raw_content, source_type: str, overrides: dict):
    """
    Register an MQ-delivered job in the api_bridge in-memory jobs dict
    AND the database, mirroring what the /render HTTP endpoint does.

    Without this, _run_pipeline's `if job_id not in jobs: abort` guard
    would silently discard every MQ-delivered job.
    """
    # Late import to avoid circular dependency at module load time
    from api_bridge import jobs, _jobs_lock, _safe_save_jobs

    now_iso = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    render_mode = (overrides or {}).get("render_mode", "auto")
    webhook_url = (overrides or {}).get("webhook_url")
    use_elevenlabs = (overrides or {}).get("use_elevenlabs", False)

    init_msg = (
        f"🚀 MQ Job initialized for topic: {topic} | "
        f"Source: {source_type.upper()} | Mode: {render_mode}"
    )

    with _jobs_lock:
        jobs[job_id] = {
            "job_id":        job_id,
            "status":        "queued",
            "video_url":     "",
            "thumbnail_url": "",
            "error":         "",
            "progress":      0,
            "current_step":  "Initializing (MQ)",
            "render_mode":   render_mode,
            "with_avatar":   False,
            "avatar_type":   None,
            "avatar_id":     None,
            "video_type":    None,
            "use_elevenlabs": use_elevenlabs,
            "image_path":    None,
            "webhook_url":   webhook_url,
            "created_at":    now_iso,
            "updated_at":    now_iso,
            "topic":         topic,
            "raw_html":      raw_content,
            "storyboard":    None,
            "overrides":     overrides,
            "idempotency_key": None,
            "logs":          [{"node": "SYSTEM", "msg": init_msg, "type": "info"}],
        }

    # Persist to disk so other workers can see the job
    _safe_save_jobs(f"MQ job registered ({job_id})")

    # DB Persistence: mirror the /render endpoint's create_job call
    try:
        from db.repository import create_job
        create_job(
            job_id=job_id,
            topic=topic,
            source_type=source_type,
            render_mode_requested=render_mode,
            with_avatar=False,
            avatar_type=None,
            callback_url=webhook_url,
        )
    except Exception as e:
        logger.warning("⚠️ MQ: DB create_job failed for %s (non-fatal): %s", job_id, e)

    logger.info("📋 MQ: Registered job %s in memory + DB", job_id)


def _on_message(channel, method, properties, body, pipeline_fn):
    """
    Called by Pika for each delivered message.
    Deserializes the JSON RenderRequest, registers the job in api_bridge,
    launches the pipeline in a worker thread, then ACKs.

    Pipeline runs in a separate thread to avoid starving Pika heartbeats
    during multi-minute renders (heartbeat=600, but renders can take 5-10min).
    """
    job_id = "unknown"
    try:
        payload = json.loads(body.decode("utf-8"))
        job_id = payload.get("jobId") or payload.get("job_id", "unknown")
        logger.info("📨 MQ: Received render job %s from queue %s", job_id, RENDER_QUEUE)

        # Determine raw_content and source_type
        raw_content = None
        source_type = "html"
        
        if payload.get("jsonData") or payload.get("json_data"):
            raw_content = payload.get("jsonData") or payload.get("json_data")
            source_type = "json"
        elif payload.get("html"):
            raw_content = payload.get("html")
            source_type = "html"
        elif payload.get("markdown"):
            raw_content = payload.get("markdown")
            source_type = "markdown"
        elif payload.get("solutionV2") or payload.get("solution_v2"):
            raw_content = payload.get("solutionV2") or payload.get("solution_v2")
            source_type = "solution_v2"
        else:
            raw_content = ""
            source_type = "html"

        # Build overrides dictionary
        overrides = payload.get("extraParams") or payload.get("extra_params") or {}
        if payload.get("renderMode") or payload.get("render_mode"):
            overrides["render_mode"] = payload.get("renderMode") or payload.get("render_mode")
        if payload.get("webhookUrl") or payload.get("webhook_url"):
            overrides["webhook_url"] = payload.get("webhookUrl") or payload.get("webhook_url")
        if payload.get("useElevenLabs") is not None:
            overrides["use_elevenlabs"] = payload.get("useElevenLabs")

        # ── FIX #2: Register job BEFORE calling pipeline_fn ──
        # Without this, _run_pipeline checks `if job_id not in jobs: abort`
        # and silently discards MQ-delivered jobs.
        _register_mq_job(job_id, payload.get("topic", ""), raw_content, source_type, overrides)

        # ── FIX #4: Run pipeline in a worker thread ──
        # The Pika callback must return quickly to avoid heartbeat starvation.
        # A multi-minute render inside the callback would starve heartbeats,
        # causing the broker to drop the connection, the ACK to fail, and the
        # message to redeliver (duplicate render).
        worker = threading.Thread(
            target=pipeline_fn,
            args=(job_id, payload.get("topic", ""), raw_content, source_type, overrides),
            daemon=True,
            name=f"mq_pipeline_{job_id}",
        )
        worker.start()
        logger.info("🚀 MQ: Dispatched job %s to worker thread", job_id)

        # ACK — message is permanently removed from queue.
        # The job is now registered and the pipeline thread is running.
        # If the pipeline fails, it updates job status to "failed" and fires
        # the webhook internally — we don't need to NACK for pipeline errors.
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("✅ MQ: ACK job %s", job_id)

    except Exception as e:
        logger.exception("❌ MQ: Failed to deserialize/register job %s — NACKing to DLQ: %s", job_id, e)
        # NACK without requeue → routes to dead letter queue
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _consumer_loop(url: str, pipeline_fn):
    """
    Blocking Pika consumer loop with automatic reconnect on connection loss.
    Runs in a background daemon thread.
    """
    import pika

    reconnect_delay = 5  # seconds

    while True:
        try:
            logger.info("🔌 MQ Consumer: Connecting to RabbitMQ at %s...",
                        url.split("@")[-1] if "@" in url else url)
            params = pika.URLParameters(url)
            # Heartbeat raised from 60→600s.  The pipeline itself now runs in a
            # separate thread (FIX #4) so the callback returns immediately, but
            # a generous heartbeat provides extra safety margin.
            params.heartbeat = 600
            params.blocked_connection_timeout = 300

            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            _ensure_topology(channel)

            channel.basic_consume(
                queue=RENDER_QUEUE,
                on_message_callback=lambda ch, method, props, body: _on_message(
                    ch, method, props, body, pipeline_fn
                ),
                auto_ack=False,
            )

            logger.info("🎧 MQ Consumer: Listening on queue '%s'...", RENDER_QUEUE)
            reconnect_delay = 5  # reset backoff on successful connect
            channel.start_consuming()

        except Exception as e:
            logger.warning(
                "⚠️ MQ Consumer: Connection error (%s). Reconnecting in %ds...",
                e, reconnect_delay
            )
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)  # exponential backoff, max 60s


def start_consumer(pipeline_fn) -> bool:
    """
    Launch the RabbitMQ consumer in a daemon thread.
    Returns True if consumer started successfully, False if MQ is not configured.

    Args:
        pipeline_fn: Callable matching the _run_pipeline signature in api_bridge.py.
                     Signature: (job_id, topic, html, source_type, overrides)
    """
    url = _get_rabbitmq_url()
    if not url:
        logger.info("ℹ️  MQ Consumer: RABBITMQ_URL not configured. Skipping consumer startup.")
        logger.info("ℹ️  Factory will accept render jobs via direct HTTP /render endpoint.")
        return False

    try:
        import pika  # noqa: F401 — verify library is installed before launching thread
    except ImportError:
        logger.warning("⚠️  MQ Consumer: 'pika' library not installed. Run: pip install pika>=1.3.0")
        return False

    thread = threading.Thread(
        target=_consumer_loop,
        args=(url, pipeline_fn),
        name="rabbitmq_consumer",
        daemon=True,
    )
    thread.start()
    logger.info("🐇 MQ Consumer thread started — subscribed to '%s'", RENDER_QUEUE)
    return True
