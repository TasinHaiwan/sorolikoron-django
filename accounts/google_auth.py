from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


def verify_google_id_token(token: str) -> dict:
    """Verifies a Google ID token and returns its decoded claims.

    Raises ValueError if the token is invalid, expired, or was issued
    for a different audience (client ID).
    """
    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), audience=settings.GOOGLE_OAUTH_CLIENT_ID
    )
