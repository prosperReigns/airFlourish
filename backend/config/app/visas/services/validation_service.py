from django.conf import settings


def validate_application(application):
    errors = {}

    if not application.visa_type:
        errors["visa_type"] = "Visa type is required"

    required_docs = getattr(settings, "REQUIRED_VISA_DOCUMENT_TYPES", [])
    documents = application.documents.all()

    if required_docs:
        missing = [
            doc_type
            for doc_type in required_docs
            if not documents.filter(document_type=doc_type).exists()
        ]
        if missing:
            errors["documents"] = f"Missing documents: {', '.join(missing)}"
    else:
        if not documents.exists():
            errors["documents"] = "At least one document is required"

    return (len(errors) == 0), errors
