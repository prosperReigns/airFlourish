from datetime import date, datetime

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

def _extract_flight_details(offer, travelers):
    details = {}
    if not isinstance(offer, dict):
        return details

    itineraries = offer.get("itineraries", [])
    first_itinerary = itineraries[0] if itineraries else {}
    segments = first_itinerary.get("segments", []) if isinstance(first_itinerary, dict) else []

    if segments:
        departure = segments[0].get("departure", {}) if isinstance(segments[0], dict) else {}
        arrival = segments[-1].get("arrival", {}) if isinstance(segments[-1], dict) else {}
        details["departure_city"] = departure.get("iataCode")
        details["arrival_city"] = arrival.get("iataCode")
        departure_at = departure.get("at")
        if isinstance(departure_at, str) and "T" in departure_at:
            details["departure_date"] = departure_at.split("T")[0]

    if isinstance(itineraries, list) and len(itineraries) > 1:
        return_itinerary = itineraries[1] if isinstance(itineraries[1], dict) else {}
        return_segments = return_itinerary.get("segments", [])
        if return_segments:
            return_departure = return_segments[0].get("departure", {})
            return_at = return_departure.get("at")
            if isinstance(return_at, str) and "T" in return_at:
                details["return_date"] = return_at.split("T")[0]

    airline_codes = offer.get("validatingAirlineCodes", [])
    if airline_codes:
        details["airline"] = airline_codes[0]
    elif segments:
        details["airline"] = segments[0].get("carrierCode")

    if isinstance(travelers, list):
        details["passengers"] = len(travelers) or 1

    return details

def format_travelers_for_amadeus(frontend_travelers):
    amadeus_travelers = []
    for idx, t in enumerate(frontend_travelers, start=1):
        # Calculate DOB from age (approximate, assumes birthday passed this year)
        birth_year = datetime.now().year - t.get("age", 30)
        dob = f"{birth_year}-01-01"  # simple default DOB, can be improved

        traveler = {
            "id": str(idx),
            "dateOfBirth": dob,
            "name": {
                "firstName": t.get("first_name", "").upper(),
                "lastName": t.get("last_name", "").upper()
            },
            "gender": t.get("gender", "MALE").upper(),  # optional, default MALE
            "contact": {
                "emailAddress": t.get("email", "example@example.com")
            },
            "documents": [
                {
                    "documentType": "PASSPORT",
                    "number": t.get("passport_number", ""),
                    "expiryDate": t.get("passport_expiry", "2030-01-01"),
                    "issuanceCountry": t.get("passport_country", "NG"),
                    "nationality": t.get("nationality", "NG"),
                    "holder": True
                }
            ]
        }
        amadeus_travelers.append(traveler)
    return amadeus_travelers
