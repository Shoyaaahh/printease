import os
import uuid

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, abort, send_from_directory
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import PrintRequest, RequestComment, Notification
from pricing import SERVICE_TYPES, PAPER_SIZES, SHIRT_SIZES, calculate_price
from file_preview import generate_preview

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')


def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


@customer_bp.before_request
def require_customer():
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    if current_user.role != 'customer':
        abort(403)


@customer_bp.route('/dashboard')
def dashboard():
    query = PrintRequest.query.filter_by(customer_id=current_user.id)
    search = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    service_type = request.args.get('service_type', '').strip()
    allowed_statuses = {'pending', 'in_queue', 'completed', 'cancelled'}

    if search:
        search_filter = PrintRequest.original_filename.ilike(f'%{search}%')
        if search.isdigit() and len(search) <= 18:
            search_filter = db.or_(search_filter, PrintRequest.id == int(search))
        query = query.filter(search_filter)
    if status in allowed_statuses:
        query = query.filter(PrintRequest.status == status)
    else:
        status = ''
    if service_type in SERVICE_TYPES:
        query = query.filter(PrintRequest.service_type == service_type)
    else:
        service_type = ''

    requests_list = query.order_by(PrintRequest.submitted_at.desc()).all()
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        'customer/dashboard.html',
        requests=requests_list,
        notifications=notifications,
        filters={'q': search, 'status': status, 'service_type': service_type},
        statuses=('pending', 'in_queue', 'completed', 'cancelled'),
        service_types=SERVICE_TYPES,
        has_filters=bool(search or status or service_type),
    )


@customer_bp.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('customer.dashboard'))


def _parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@customer_bp.route('/submit', methods=['GET', 'POST'])
def submit_request():
    if request.method == 'POST':
        file = request.files.get('design_file')
        service_type = request.form.get('service_type', '')
        copies_raw = request.form.get('copies', '1')
        is_urgent = request.form.get('is_urgent') == 'on'
        is_colored = request.form.get('is_colored') == 'on'

        # service-specific raw inputs
        paper_size = request.form.get('paper_size', '').strip()
        page_count_raw = request.form.get('page_count', '').strip()
        width_ft_raw = request.form.get('width_ft', '').strip()
        height_ft_raw = request.form.get('height_ft', '').strip()
        shirt_size = request.form.get('shirt_size', '').strip()
        shirt_color = request.form.get('shirt_color', '').strip()

        errors = []

        if service_type not in SERVICE_TYPES:
            errors.append('Please choose what you want printed.')

        if not file or file.filename == '':
            errors.append('Please attach a file to print.')
        elif not allowed_file(file.filename):
            errors.append('That file type is not supported.')

        copies = _parse_int(copies_raw, default=None)
        if not copies or copies < 1:
            errors.append('Copies must be a positive whole number.')
            copies = 1

        page_count = _parse_int(page_count_raw, default=None)
        width_ft = _parse_float(width_ft_raw, default=None)
        height_ft = _parse_float(height_ft_raw, default=None)

        # Validate the fields that matter for the chosen service type
        if service_type in ('document_print', 'soft_bind', 'hard_bind', 'laminate'):
            if not paper_size or paper_size not in PAPER_SIZES:
                errors.append('Please select a paper size.')
        if service_type in ('document_print', 'soft_bind', 'hard_bind'):
            if not page_count or page_count < 1:
                errors.append('Please enter the number of pages.')
        if service_type == 'tarpaulin':
            if not width_ft or not height_ft or width_ft <= 0 or height_ft <= 0:
                errors.append('Please enter a valid tarpaulin width and height (in feet).')
            is_colored = True  # tarpaulins are always printed in color
        if service_type == 'shirt_print':
            if shirt_size not in SHIRT_SIZES:
                errors.append('Please select a shirt size.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'customer/submit_request.html',
                service_types=SERVICE_TYPES, paper_sizes=PAPER_SIZES,
                shirt_sizes=SHIRT_SIZES, form=request.form,
            )

        original_filename = secure_filename(file.filename)
        stored_filename = f'{uuid.uuid4().hex}_{original_filename}'
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(file_path)

        preview_filename = generate_preview(file_path, stored_filename, current_app.config['UPLOAD_FOLDER'])

        estimated_price = calculate_price(
            service_type=service_type,
            copies=copies,
            is_colored=is_colored,
            page_count=page_count,
            width_ft=width_ft,
            height_ft=height_ft,
            is_urgent=is_urgent,
        )

        new_request = PrintRequest(
            customer_id=current_user.id,
            service_type=service_type,
            filename=stored_filename,
            original_filename=original_filename,
            preview_filename=preview_filename,
            copies=copies,
            paper_size=paper_size or None,
            is_colored=is_colored,
            page_count=page_count,
            width_ft=width_ft,
            height_ft=height_ft,
            shirt_size=shirt_size or None,
            shirt_color=shirt_color or None,
            is_urgent=is_urgent,
            estimated_price=estimated_price,
            status='pending',
        )
        db.session.add(new_request)
        db.session.commit()
        flash(
            f'Your print request has been submitted! Estimated price: '
            f'{new_request.formatted_price} (the shop will confirm the final price).',
            'success',
        )
        return redirect(url_for('customer.request_detail', request_id=new_request.id))

    return render_template(
        'customer/submit_request.html',
        service_types=SERVICE_TYPES, paper_sizes=PAPER_SIZES,
        shirt_sizes=SHIRT_SIZES, form={},
    )


@customer_bp.route('/request/<int:request_id>', methods=['GET', 'POST'])
def request_detail(request_id):
    print_request = PrintRequest.query.get_or_404(request_id)
    if print_request.customer_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        comment_text = request.form.get('comment_text', '').strip()
        if comment_text:
            db.session.add(RequestComment(
                print_request_id=print_request.id,
                author_id=current_user.id,
                comment_text=comment_text,
            ))
            db.session.commit()
            flash('Your note has been added to the request.', 'success')
        else:
            flash('Please write something before submitting.', 'warning')
        return redirect(url_for('customer.request_detail', request_id=request_id))

    return render_template('customer/request_detail.html', req=print_request)


@customer_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    print_request = PrintRequest.query.filter(
        (PrintRequest.filename == filename) | (PrintRequest.preview_filename == filename)
    ).first_or_404()
    if print_request.customer_id != current_user.id:
        abort(403)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
