import json
import os

from kafka import KafkaProducer

_producer = None


def _get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        bootstrap = os.environ.get("REDPANDA_BROKERS", "localhost:9092")
        _producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            api_version=(2, 0, 0),
        )
    return _producer


_US_ENTITIES = {"us_equity", "us_index"}


def publish_signal(payload: dict) -> None:
    entity = payload.get("mode", "").lower()
    if entity in _US_ENTITIES:
        topic = os.environ.get("SIGNALS_TOPIC_US", "parallax-signals-us")
    else:
        topic = os.environ.get("SIGNALS_TOPIC_INDIA", "parallax-signals-india")
    _get_producer().send(topic, value=payload)
