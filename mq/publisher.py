import pika
import json
import os
import logging

logger = logging.getLogger("video_factory.mq_publisher")

def publish_render_job(payload: dict) -> bool:
    """Publishes a render job request to the RabbitMQ exchange."""
    from mq.consumer import _get_rabbitmq_url, EXCHANGE, RENDER_ROUTING_KEY
    url = _get_rabbitmq_url()
    if not url:
        logger.warning("RABBITMQ_URL not configured. Cannot publish job.")
        return False
    try:
        params = pika.URLParameters(url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Ensure exchange is declared
        channel.exchange_declare(
            exchange=EXCHANGE,
            exchange_type="direct",
            durable=True,
        )
        
        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=RENDER_ROUTING_KEY,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type="application/json",
            )
        )
        connection.close()
        logger.info("✅ Successfully published job %s to RabbitMQ queue", payload.get("job_id") or payload.get("jobId"))
        return True
    except Exception as e:
        logger.error("❌ Failed to publish job to RabbitMQ: %s", e)
        return False
