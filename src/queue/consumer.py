import json
import os

from kafka import KafkaConsumer

from src.orders.order_placement import OrderPlacer


def consume(market: str):
    bootstrap = os.environ.get("REDPANDA_BROKERS", "localhost:9092")

    if market == "us":
        topic    = os.environ.get("SIGNALS_TOPIC_US", "parallax-signals-us")
        group_id = "order-placement-us"
    else:
        topic    = os.environ.get("SIGNALS_TOPIC_INDIA", "parallax-signals-india")
        group_id = "order-placement-india"

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id=group_id,
        api_version=(2, 0, 0),
    )

    placer = OrderPlacer(market)
    print(f"consumer: market={market} topic={topic} brokers={bootstrap}")

    for message in consumer:
        payload = message.value
        entity  = payload.get("mode")
        signals = payload.get("signals", [])

        if not signals:
            continue

        print(f"consumer: offset={message.offset} entity={entity} signals={len(signals)}")
        print(placer.place_orders([payload], entity))
