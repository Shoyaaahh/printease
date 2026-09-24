import os
from flask import Flask, redirect, url_for
from flask_login import current_user

from config import Config
from extensions import db, login_manager, mail
from models import User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to continue.'
    login_manager.login_message_category = 'info'

    from auth.routes import auth_bp
    from customer.routes import customer_bp
    from admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.dashboard'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    """Create a default admin account on first run so there's always a way in."""
    from werkzeug.security import generate_password_hash

    admin = User.query.filter_by(email='admin@printease.com').first()
    if not admin:
        admin = User(
            full_name='PrintEase Admin',
            email='admin@printease.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
        )
        db.session.add(admin)
        db.session.commit()
        print('Seeded default admin -> email: admin@printease.com | password: admin123')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
