"""Public, non-secret metadata verified by offline APK analysis."""

from __future__ import annotations

AWS_REGION = "us-east-1"
IOT_ENDPOINT = "a2bby18smixe1f-ats.iot.us-east-1.amazonaws.com"
PROVISIONING_METHOD = "POST"
PROVISIONING_PATH = "/cradles/pairedUsers/v3"

SHADOW_TOPIC_SHAPES = (
    "$aws/things/{thingName}/shadow/get",
    "$aws/things/{thingName}/shadow/get/accepted",
    "$aws/things/{thingName}/shadow/get/rejected",
)
