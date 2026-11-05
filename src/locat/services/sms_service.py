"""Sending SMS: a console simulator for development, Africa's Talking for real."""
import logging

from locat.config import get_settings

logger = logging.getLogger("locat.sms")
_sdk_ready = False


def _init_sdk() -> None:
    global _sdk_ready
    if _sdk_ready:
        return
    import africastalking

    settings = get_settings()
    africastalking.initialize(settings.at_username, settings.at_api_key)
    _sdk_ready = True


def send_sms(phone: str, message: str) -> bool:
    """Send one SMS. Never raises: a failed SMS must not break a booking."""
    settings = get_settings()

    if settings.sms_mode != "africastalking":
        print(f"\n[SMS -> {phone}]\n{message}\n", flush=True)
        return True

    try:
        _init_sdk()
        import africastalking

        kwargs = {"sender_id": settings.at_sender_id} if settings.at_sender_id else {}
        response = africastalking.SMS.send(message, [phone], **kwargs)
        print(f"[SMS sent -> {phone}] {response}", flush=True)
        return True
    except Exception:
        logger.exception("SMS to %s failed", phone)
        return False