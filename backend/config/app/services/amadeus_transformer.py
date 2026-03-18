from datetime import date, timedelta

def _get_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None

def _is_amadeus_traveler(traveler):
    if not isinstance(traveler, dict):
        return False
    if "dateOfBirth" not in traveler:
        return False
    name = traveler.get("name")
    if not isinstance(name, dict):
        return False
    return "firstName" in name and "lastName" in name

def ensure_amadeus_travelers(travelers):
    if isinstance(travelers, list) and travelers:
        if all(_is_amadeus_traveler(t) for t in travelers):
            return travelers
    return normalize_travelers(travelers)

def normalize_travelers(travelers):
    normalized = []

    for i, t in enumerate(travelers, start=1):
        # Try explicit DOB first, fallback to age-based DOB.
        dob = _get_value(t, "dateOfBirth", "dob", "date_of_birth")
        if not dob:
            age_value = _get_value(t, "age")
            try:
                age_value = int(age_value) if age_value is not None else 30
            except (TypeError, ValueError):
                age_value = 30
            dob_year = date.today().year - age_value
            dob = f"{dob_year}-01-01"

        first_name = _get_value(t, "first_name", "firstName", "firstname", "first")
        last_name = _get_value(t, "last_name", "lastName", "lastname", "last")
        if not first_name:
            first_name = "UNKNOWN"
        if not last_name:
            last_name = "UNKNOWN"
        raw_gender = t.get("gender") or t.get("sex")
        gender = None
        if raw_gender:
            gender = str(raw_gender).upper()
            if gender in {"M", "MALE"}:
                gender = "MALE"
            elif gender in {"F", "FEMALE"}:
                gender = "FEMALE"
        if not gender:
            gender = "MALE"

        traveler = {
            "id": str(i),
            "dateOfBirth": dob,
            "name": {
                "firstName": str(first_name).upper(),
                "lastName": str(last_name).upper()
            },
            "gender": gender,
        }

        passport_number = _get_value(t, "passport_number", "passportNumber")
        if passport_number:
            traveler["documents"] = [
                {
                    "documentType": "PASSPORT",
                    "number": passport_number,
                    "expiryDate": _get_value(
                        t,
                        "passport_expiry",
                        "passportExpiry",
                        "passport_expiry_date",
                        "passportExpiryDate",
                    ) or "2030-01-01",
                    "issuanceCountry": _get_value(
                        t,
                        "passport_country",
                        "issuanceCountry",
                        "issuance_country",
                    ) or "NG",
                    "nationality": _get_value(t, "nationality") or "NG",
                    "holder": True,
                }
            ]

        email = _get_value(t, "email", "emailAddress")
        phone = _get_value(t, "phone", "phone_number", "phoneNumber")
        if email or phone:
            traveler["contact"] = {}
            if email:
                traveler["contact"]["emailAddress"] = email
            if phone:
                traveler["contact"]["phones"] = [
                    {
                        "deviceType": "MOBILE",
                        "countryCallingCode": "234",
                        "number": str(phone),
                    }
                ]

        normalized.append(traveler)

    return normalized
