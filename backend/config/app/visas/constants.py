def normalize_visa_type(value):
    return str(value or "").strip().lower().replace(" ", "_")


VISA_TYPE_DOCUMENT_TEMPLATE = {
    "NG": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "US": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "GB": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "CA": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "AU": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "DE": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "FR": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "AE": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "ZA": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
    "IN": {
        "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
        "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
        "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
        "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
    },
}


def get_default_documents(country, visa_type_name):
    country_code = str(country or "").strip().upper()
    visa_key = normalize_visa_type(visa_type_name)
    if not country_code or not visa_key:
        return []
    return list(VISA_TYPE_DOCUMENT_TEMPLATE.get(country_code, {}).get(visa_key, []))
