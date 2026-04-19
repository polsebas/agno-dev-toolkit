import time  # ← anti-pattern: ASYNC_REQUIRED will flag this


def send_welcome_email(user_email: str, user_name: str) -> dict:
    """
    Send a welcome email to a new user.
    Use this tool when a user completes registration and needs a welcome message.
    """
    time.sleep(2)  # ← INTENTIONAL anti-pattern for demo
    return {"status": "sent", "recipient": user_email}
