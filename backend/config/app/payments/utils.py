from copy import deepcopy


SENSITIVE_FLUTTERWAVE_FIELDS = {"card", "authorization"}


def sanitize_flutterwave_payload(payload):
    if not isinstance(payload, dict):
        return payload

    sanitized = deepcopy(payload)

    for field in SENSITIVE_FLUTTERWAVE_FIELDS:
        sanitized.pop(field, None)

    data = sanitized.get("data")
    if isinstance(data, dict):
        for field in SENSITIVE_FLUTTERWAVE_FIELDS:
            data.pop(field, None)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for field in SENSITIVE_FLUTTERWAVE_FIELDS:
                    item.pop(field, None)

    return sanitized
