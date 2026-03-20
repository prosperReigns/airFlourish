from django.conf import settings
from app.visas.constants import get_default_documents


def validate_application(application):
    errors = {}

    if not application.visa_type:
        errors["visa_type"] = "Visa type is required"

    required_docs = []
    if application.visa_type and isinstance(application.visa_type.required_documents, list):
        required_docs = application.visa_type.required_documents
    if not required_docs:
        if application.visa_type:
            required_docs = get_default_documents(
                application.visa_type.country,
                application.visa_type.name or application.visa_type.code,
            )
    if not required_docs:
        required_docs = getattr(settings, "REQUIRED_VISA_DOCUMENT_TYPES", [])
    documents = application.documents.all()

    if required_docs:
        missing = []
        for doc_type in required_docs:
            document_qs = list(documents.filter(document_type=doc_type))
            if not document_qs:
                missing.append(doc_type)
                continue
            if not any(getattr(doc.file, "size", 0) for doc in document_qs if doc.file):
                missing.append(doc_type)
        if missing:
            errors["documents"] = f"Missing documents: {', '.join(missing)}"
    else:
        if not any(getattr(doc.file, "size", 0) for doc in documents if doc.file):
            errors["documents"] = "At least one document is required"

    quality_errors = application.document_quality_errors(required_docs)
    if quality_errors:
        errors["document_quality"] = quality_errors

    return (len(errors) == 0), errors
