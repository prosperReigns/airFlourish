import requests
from django.conf import settings


def verify_captcha(token):

    url = "https://www.google.com/recaptcha/api/siteverify"

    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": token
    }

    response = requests.post(url, data=payload)

    result = response.json()

    return result.get("success", False)