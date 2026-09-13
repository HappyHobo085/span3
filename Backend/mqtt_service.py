"""MQTT publisher helper for MOON emergency messages."""

import json
import os
from typing import Any, Dict

from paho.mqtt import publish


MQTT_HOST = os.getenv("MQTT_HOST", "mqtt").strip() or "mqtt"
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = (
    os.getenv("MQTT_TOPIC_PREFIX", "moon/noodgeval").strip().strip("/")
    or "moon/noodgeval"
)
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "").strip()
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")


def topic_for_campus(kampus_id: int) -> str:
    """Canonical MQTT topic for one campus."""
    return f"{MQTT_TOPIC_PREFIX}/kampus/{int(kampus_id)}"


def publish_json(
    topic: str,
    payload: Dict[str, Any],
    *,
    qos: int = 1,
    retain: bool = False,
) -> None:
    """Publish one JSON message to the configured MQTT broker."""
    auth = None
    if MQTT_USERNAME:
        auth = {
            "username": MQTT_USERNAME,
            "password": MQTT_PASSWORD,
        }

    publish.single(
        topic,
        payload=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        qos=qos,
        retain=retain,
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        auth=auth,
        keepalive=20,
    )
