"""
RabbitMQ Consumer — EaseToLearn Video Factory

Subscribes to the etl.video.render.queue and processes render jobs
dispatched by the Spring Boot integration service.

Architecture:
    Spring Boot publishes RenderRequest JSON → RabbitMQ → This consumer
    → Deserializes JSON → Calls _run_pipeline() → ACKs message
    → On exception → NACKs message (routes to etl.video.render.dlq)

Graceful degradation:
    If RABBITMQ_URL is not set, the consumer silently skips startup
    and the factory falls back to direct HTTP /render endpoint mode.
"""

import json
import logging
import os
import threading
import time
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


def _on_message(channel, method, properties, body, pipeline_fn):
    """
    Called by Pika for each delivered message.
    Deserializes the JSON RenderRequest from Spring Boot,
    runs the LangGraph pipeline, then ACKs or NACKs.
    """
    job_id = "unknown"
    try:
        payload = json.loads(body.decode("utf-8"))
        job_id = payload.get("jobId") or payload.get("job_id", "unknown")
        logger.info("📨 MQ: Received render job %s from queue %s", job_id, RENDER_QUEUE)

        # Build the kwargs expected by _run_pipeline (api_bridge.py)
        pipeline_fn(
            job_id=job_id,
            topic=payload.get("topic", ""),
            html=payload.get("html"),
            solution_v2=payload.get("solutionV2") or payload.get("solution_v2"),
            json_data=payload.get("jsonData") or payload.get("json_data"),
            markdown=payload.get("markdown"),
            render_mode=payload.get("renderMode") or payload.get("render_mode"),
            webhook_url=payload.get("webhookUrl") or payload.get("webhook_url"),
            use_elevenlabs=payload.get("useElevenLabs", False),
            extra_params=payload.get("extraParams") or payload.get("extra_params") or {},
        )

        # ACK — message is permanently removed from queue
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("✅ MQ: ACK job %s", job_id)

    except Exception as e:
        logger.exception("❌ MQ: Pipeline failed for job %s — NACKing to DLQ: %s", job_id, e)
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
            params.heartbeat = 60
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
                     Receives deserialized render job kwargs and executes the pipeline.
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
