"""
Central place for notifying a customer about their print request.

- In-app notifications (the Notification model) always work, no setup needed.
- Email is sent through Flask-Mail IF the MAIL_SERVER config is set. If it's
  left blank (the default), email sending is silently skipped so the app
  keeps working out of the box.
- SMS is stubbed out below. Wiring it up needs a paid SMS API account (e.g.
  Semaphore, which is commonly used in the Philippines, or Twilio) and your
  own API key - see the comment in _send_sms_safely for how to enable it.
"""

from flask import current_app
from flask_mail import Message

from extensions import db, mail
from models import Notification


def notify_customer(user, message, print_request=None):
    """Create an in-app notification and try to also email/SMS the customer."""
    db.session.add(Notification(
        user_id=user.id,
        print_request_id=print_request.id if print_request else None,
        message=message,
    ))
    db.session.commit()

    _send_email_safely(user, message)
    _send_sms_safely(user, message)


def _send_email_safely(user, message):
    if not current_app.config.get('MAIL_SERVER'):
        return  # email not configured - in-app notification is still saved above
    try:
        msg = Message(
            subject="PrintEase Update - Marian's Printing Services",
            recipients=[user.email],
            body=message,
        )
        mail.send(msg)
    except Exception as exc:  # never let a failed email break the request flow
        current_app.logger.warning(f'Could not send email notification: {exc}')


def _send_sms_safely(user, message):
    phone_number = getattr(user, 'phone_number', None)
    if not phone_number:
        return

    api_key = current_app.config.get('SEMAPHORE_API_KEY')
    if not api_key:
        # No SMS provider configured - just log what would have been sent.
        current_app.logger.info(f'[SMS not configured] Would text {phone_number}: {message}')
        return

    try:
        import requests  # only needed if you actually enable SMS
        requests.post(
            'https://api.semaphore.co/api/v4/messages',
            data={
                'apikey': api_key,
                'number': phone_number,
                'message': message,
            },
            timeout=5,
        )
    except Exception as exc:
        current_app.logger.warning(f'Could not send SMS notification: {exc}')
