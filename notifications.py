"""
Central place for notifying a customer about their print request.

- In-app notifications (the Notification model) always work, no setup needed.
- Email is sent through Flask-Mail IF the MAIL_SERVER config is set. If it's
  left blank (the default), email sending is silently skipped so the app
  keeps working out of the box.
- SMS is sent through Semaphore when SEMAPHORE_API_KEY is configured. Without
  credentials, SMS is skipped and in-app notifications continue to work.
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
        current_app.logger.info('[SMS not configured] Skipping customer SMS notification.')
        return

    try:
        import requests
        response = requests.post(
            'https://api.semaphore.co/api/v4/messages',
            data={
                'apikey': api_key,
                'number': phone_number,
                'message': message,
                **({'sendername': current_app.config['SEMAPHORE_SENDERNAME']}
                   if current_app.config.get('SEMAPHORE_SENDERNAME') else {}),
            },
            timeout=10,
        )
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError:
            current_app.logger.warning('Semaphore returned an invalid SMS response.')
            return

        results = result if isinstance(result, list) else [result]
        if not results or any(
            not isinstance(item, dict)
            or str(item.get('status', '')).lower() not in {'queued', 'pending', 'sent'}
            for item in results
        ):
            current_app.logger.warning('Semaphore rejected an SMS notification (recipient omitted).')
    except Exception as exc:  # never let a failed SMS break the request flow
        current_app.logger.warning(f'Could not send SMS notification: {exc}')
