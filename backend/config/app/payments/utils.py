SENSITIVE_FLUTTERWAVE_FIELDS = {"card", "authorization"}


def sanitize_flutterwave_payload(payload):
    if not isinstance(payload, dict):
        return payload

    sanitized = dict(payload)

    for field in SENSITIVE_FLUTTERWAVE_FIELDS:
        sanitized.pop(field, None)

    data = sanitized.get("data")
    if isinstance(data, dict):
        sanitized_data = dict(data)
        for field in SENSITIVE_FLUTTERWAVE_FIELDS:
            sanitized_data.pop(field, None)
        sanitized["data"] = sanitized_data
    elif isinstance(data, list):
        sanitized_list = []
        for item in data:
            if isinstance(item, dict):
                sanitized_item = dict(item)
                for field in SENSITIVE_FLUTTERWAVE_FIELDS:
                    sanitized_item.pop(field, None)
                sanitized_list.append(sanitized_item)
            else:
                sanitized_list.append(item)
        sanitized["data"] = sanitized_list

    return sanitized
