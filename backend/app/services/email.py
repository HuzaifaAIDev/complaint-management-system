from flask import current_app
from flask_mail import Message
from app.extensions import mail


def _send(to_email: str, subject: str, body: str):
    """Sends a plain-text email. If no SMTP server is configured
    (MAIL_SUPPRESS_SEND), the message is logged server-side instead so the
    application remains fully functional in local development without
    requiring real email credentials. In any real deployment, MAIL_SERVER
    must be set in the environment for OTP/reset emails to actually be
    delivered."""
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.info("[DEV EMAIL - no MAIL_SERVER configured] To: %s | Subject: %s\n%s", to_email, subject, body)
        return

    msg = Message(subject=subject, recipients=[to_email], body=body)
    mail.send(msg)


def send_otp_email(to_email: str, code: str, purpose: str):
    if purpose == "signup_verification":
        subject = "Verify your email"
        body = (
            f"Your verification code is: {code}\n\n"
            f"This code expires in {current_app.config['OTP_EXPIRY_MINUTES']} minutes. "
            "If you did not create an account, you can safely ignore this email."
        )
    else:
        subject = "Password reset code"
        body = (
            f"Your password reset code is: {code}\n\n"
            f"This code expires in {current_app.config['OTP_EXPIRY_MINUTES']} minutes. "
            "If you did not request a password reset, you can safely ignore this email."
        )
    _send(to_email, subject, body)


def send_temporary_password_email(to_email: str, temporary_password: str):
    subject = "Your temporary password"
    body = (
        f"Your temporary password is: {temporary_password}\n\n"
        "For your security, you will be required to set a new password immediately "
        "after logging in with this temporary one. If you did not request this, "
        "please contact your administrator."
    )
    _send(to_email, subject, body)
