from datetime import datetime
from flask_login import UserMixin
from extensions import db
from pricing import SERVICE_TYPES, CURRENCY_SYMBOL


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # 'customer' or 'admin'
    customer_type = db.Column(db.String(20), nullable=True)  # 'normal' or 'student'
    student_id = db.Column(db.String(20), nullable=True)  # format XX-XXXXX
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    print_requests = db.relationship(
        'PrintRequest', backref='customer', lazy=True,
        foreign_keys='PrintRequest.customer_id'
    )

    def __repr__(self):
        return f'<User {self.email}>'


class PrintRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # What the customer wants: document_print, tarpaulin, shirt_print, soft_bind, hard_bind, laminate
    service_type = db.Column(db.String(30), nullable=False, default='document_print')

    filename = db.Column(db.String(255), nullable=False)          # name stored on disk
    original_filename = db.Column(db.String(255), nullable=False)  # name the user uploaded
    preview_filename = db.Column(db.String(255), nullable=True)   # generated thumbnail (if any)

    copies = db.Column(db.Integer, nullable=False, default=1)

    # Document print / soft & hard bind / laminate
    paper_size = db.Column(db.String(30), nullable=True)
    is_colored = db.Column(db.Boolean, default=False)
    page_count = db.Column(db.Integer, nullable=True)

    # Tarpaulin
    width_ft = db.Column(db.Float, nullable=True)
    height_ft = db.Column(db.Float, nullable=True)

    # Shirt printing
    shirt_size = db.Column(db.String(10), nullable=True)
    shirt_color = db.Column(db.String(30), nullable=True)

    is_urgent = db.Column(db.Boolean, default=False)
    estimated_price = db.Column(db.Float, nullable=True)

    status = db.Column(db.String(30), default='pending')  # pending, in_queue, completed, cancelled
    admin_notes = db.Column(db.Text, nullable=True)
    completion_date = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    comments = db.relationship(
        'RequestComment', backref='print_request', lazy=True,
        cascade='all, delete-orphan', order_by='RequestComment.created_at'
    )

    @property
    def is_priority(self):
        """A request is in the priority lane if it's marked urgent OR the customer is a student."""
        return bool(self.is_urgent or (self.customer and self.customer.customer_type == 'student'))

    @property
    def status_label(self):
        return {
            'pending': 'Pending Review',
            'in_queue': 'On Queue',
            'completed': 'Completed',
            'cancelled': 'Cancelled',
        }.get(self.status, self.status)

    @property
    def status_badge(self):
        return {
            'pending': 'secondary',
            'in_queue': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
        }.get(self.status, 'secondary')

    @property
    def service_type_label(self):
        return SERVICE_TYPES.get(self.service_type, self.service_type)

    @property
    def formatted_price(self):
        if self.estimated_price is None:
            return '—'
        return f'{CURRENCY_SYMBOL}{self.estimated_price:,.2f}'

    @property
    def display_specs(self):
        """One-line summary of the service-specific details, for tables."""
        if self.service_type == 'document_print':
            parts = [self.paper_size or '', 'Color' if self.is_colored else 'B/W']
            if self.page_count:
                parts.append(f'{self.page_count}pg')
            return ', '.join(p for p in parts if p)

        if self.service_type == 'tarpaulin':
            if self.width_ft and self.height_ft:
                return f'{self.width_ft:g}ft x {self.height_ft:g}ft'
            return '—'

        if self.service_type == 'shirt_print':
            parts = []
            if self.shirt_size:
                parts.append(f'Size {self.shirt_size}')
            if self.shirt_color:
                parts.append(self.shirt_color)
            return ', '.join(parts) if parts else '—'

        if self.service_type in ('soft_bind', 'hard_bind'):
            parts = [self.paper_size or '']
            if self.page_count:
                parts.append(f'{self.page_count}pg')
            parts.append('Color' if self.is_colored else 'B/W')
            return ', '.join(p for p in parts if p)

        if self.service_type == 'laminate':
            return self.paper_size or '—'

        return '—'

    def __repr__(self):
        return f'<PrintRequest {self.id} - {self.status}>'


class RequestComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    print_request_id = db.Column(db.Integer, db.ForeignKey('print_request.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', foreign_keys=[author_id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    print_request_id = db.Column(db.Integer, db.ForeignKey('print_request.id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
