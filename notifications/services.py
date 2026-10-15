import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_init_attempted = False
_firebase_init_lock = threading.Lock()


def _get_firebase_app():
    """
    Lazily initializes the firebase_admin app from FIREBASE_CREDENTIALS_PATH.
    Returns None (and logs once) if it isn't configured or fails to load —
    callers must treat that as "sending is a no-op", never as an error.
    """
    global _firebase_app, _firebase_init_attempted

    if _firebase_init_attempted:
        return _firebase_app

    with _firebase_init_lock:
        if _firebase_init_attempted:
            return _firebase_app

        _firebase_init_attempted = True
        credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
        if not credentials_path:
            logger.warning("FIREBASE_CREDENTIALS_PATH is not set — push notifications are disabled.")
            return None

        try:
            import firebase_admin
            from firebase_admin import credentials

            _firebase_app = firebase_admin.initialize_app(credentials.Certificate(credentials_path))
        except Exception:
            logger.exception("Failed to initialize firebase_admin — push notifications are disabled.")
            _firebase_app = None

        return _firebase_app


def send_push(user, title, body, data=None):
    """
    Sends a push to every device registered to `user`. Never raises —
    any failure (misconfigured credentials, network error, invalid
    token) is logged and swallowed, so a failed push never breaks the
    caller's request. Stale tokens (unregistered on the device) are
    cleaned up automatically.
    """
    from .models import DeviceToken

    try:
        app = _get_firebase_app()
        if app is None:
            return

        from firebase_admin import messaging

        tokens = list(user.device_tokens.order_by("id").values_list("id", "token"))
        if not tokens:
            return

        string_data = {str(k): str(v) for k, v in (data or {}).items()}
        messages = [
            messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=string_data,
            )
            for _, token in tokens
        ]

        responses = messaging.send_each(messages, app=app)
        for (token_id, token), response in zip(tokens, responses.responses):
            if response.success:
                continue
            exception = response.exception
            if isinstance(exception, messaging.UnregisteredError):
                DeviceToken.objects.filter(id=token_id).delete()
            else:
                logger.warning("Push to token id=%s failed: %s", token_id, exception)
    except Exception:
        logger.exception("send_push failed for user id=%s", getattr(user, "id", None))


def dispatch_push(user, title, body, data=None):
    """
    Fire-and-forget wrapper around send_push — runs it on a daemon
    thread so a slow/hung FCM call never blocks the request that
    triggered it. There's no celery/task queue in this project; this is
    the zero-new-infra way to keep sending non-blocking.
    """
    thread = threading.Thread(target=send_push, args=(user, title, body, data), daemon=True)
    thread.start()
