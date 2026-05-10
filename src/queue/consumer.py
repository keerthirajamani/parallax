import json
import os

from kafka import KafkaConsumer

from src.orders.order_placement import OrderPlacer


def consume():
    bootstrap = os.environ.get("REDPANDA_BROKERS", "localhost:9092")
    topic     = os.environ.get("SIGNALS_TOPIC", "parallax-signals")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="order-placement",
        api_version=(2, 0, 0),
    )

    placer = OrderPlacer()
    print(f"consumer: listening on topic={topic} brokers={bootstrap}")

    for message in consumer:
        payload = message.value
        entity  = payload.get("mode")
        signals = payload.get("signals", [])

        if not signals:
            continue

        print(f"consumer: offset={message.offset} entity={entity} signals={len(signals)}")
        placer.place_orders([payload], entity)
