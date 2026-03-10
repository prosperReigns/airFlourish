import uuid

def generate_booking_reference(service_type: str) -> str:
        prefix = service_type.upper()[:3]
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}-{unique_id}"
