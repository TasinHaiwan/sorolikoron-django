from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth as firebase_auth
from .models import Customer, Representative


class FirebaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None

        token = header.removeprefix("Bearer ").strip()
        try:
            decoded = firebase_auth.verify_id_token(token)
        except Exception:
            raise AuthenticationFailed("Invalid or expired Firebase token")

        customer, _ = Customer.objects.get_or_create(
            firebase_uid=decoded["uid"],
            defaults={
                "name": decoded.get("name", ""),
                "email": decoded.get("email", ""),
            },
        )
        return (customer, None)

class RepresentativeAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.removeprefix("Bearer ").strip()
        try:
            decoded = firebase_auth.verify_id_token(token)
        except Exception:
            raise AuthenticationFailed("Invalid or expired Firebase token")

        uid = decoded["uid"]
        email = decoded.get("email", "")

        rep = Representative.objects.filter(firebase_uid=uid).first()
        if rep is None and email:
            # First sign-in: claim the admin-created record by matching email
            rep = Representative.objects.filter(email__iexact=email, firebase_uid__isnull=True).first()
            if rep:
                rep.firebase_uid = uid
                rep.save(update_fields=["firebase_uid"])
        if rep is None:
            raise AuthenticationFailed(
                "No representative account found for this account. Contact admin."
            )
        return (rep, None)