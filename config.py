import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'printease.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'psd', 'ai', 'pptx', 'svg'}
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB max upload

    # --- Email notifications (optional) ---
    # Leave MAIL_SERVER unset/empty to run with in-app notifications only
    # (nothing breaks - emails are just skipped). Fill these in with your own
    # SMTP provider (Gmail App Password, SendGrid, etc.) to enable real email.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@printease.local')

    # --- SMS notifications (optional, provider not wired in) ---
    # See notifications.py for how to plug in a provider like Semaphore/Twilio.
    SEMAPHORE_API_KEY = os.environ.get('SEMAPHORE_API_KEY', '')
