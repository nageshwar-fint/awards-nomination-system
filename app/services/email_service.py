"""Email service for sending emails (password reset, etc.)."""
import smtplib
import structlog
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


def send_password_reset_email(user_email: str, user_name: str, reset_token: str) -> bool:
    """
    Send password reset email to user.
    
    Args:
        user_email: User's email address
        user_name: User's name
        reset_token: Password reset token
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Build reset link
        reset_link = f"{settings.frontend_base_url}/reset-password?token={reset_token}"
        
        # Create email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset Your Password - Awards Nomination System"
        msg["From"] = settings.smtp_from_email
        msg["To"] = user_email
        
        # Create email body
        text = f"""
Hello {user_name},

You requested to reset your password for the Awards Nomination System. Click the link below to reset it:

{reset_link}

This link will expire in {settings.password_reset_token_expire_hours} hour(s).

If you didn't request this, please ignore this email and your password will remain unchanged.

Best regards,
Awards Nomination System
"""
        
        html = f"""
<html>
  <body>
    <p>Hello {user_name},</p>
    <p>You requested to reset your password for the Awards Nomination System. Click the link below to reset it:</p>
    <p><a href="{reset_link}">{reset_link}</a></p>
    <p>This link will expire in {settings.password_reset_token_expire_hours} hour(s).</p>
    <p>If you didn't request this, please ignore this email and your password will remain unchanged.</p>
    <p>Best regards,<br>Awards Nomination System</p>
  </body>
</html>
"""
        
        # Attach parts
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        if settings.smtp_host == "localhost" or not settings.smtp_user:
            # In development, just log the email
            logger.info(
                "password_reset_email_sent",
                email=user_email,
                reset_link=reset_link,
                note="Email not sent (local development mode)"
            )
            return True
        
        # Connect to SMTP server
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        
        server.send_message(msg)
        server.quit()
        
        logger.info("password_reset_email_sent", email=user_email)
        return True
        
    except Exception as e:
        logger.error("failed_to_send_password_reset_email", email=user_email, error=str(e), exc_info=True)
        return False
