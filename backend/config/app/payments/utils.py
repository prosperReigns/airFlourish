SENSITIVE_FLUTTERWAVE_FIELDS = {"card", "authorization"}


def _sanitize_value(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_value(val)
            for key, val in value.items()
            if key not in SENSITIVE_FLUTTERWAVE_FIELDS
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def sanitize_flutterwave_payload(payload):
    if not isinstance(payload, dict):
        return payload

    return _sanitize_value(payload)
