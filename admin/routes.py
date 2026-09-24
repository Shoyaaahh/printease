from datetime import datetime
import math

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, abort, current_app, send_from_directory
)
from flask_login import current_user

from extensions import db
from models import PrintRequest, User
from pricing import SERVICE_TYPES, PAPER_SIZES, SHIRT_SIZES, calculate_price
from notifications import notify_customer

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

STATUSES = ['pending', 'in_queue', 'completed', 'cancelled']


@admin_bp.before_request
def require_admin():
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    if current_user.role != 'admin':
        abort(403)


@admin_bp.route('/dashboard')
def dashboard():
    active_requests = (
        PrintRequest.query.filter(PrintRequest.status.in_(['pending', 'in_queue']))
        .order_by(PrintRequest.submitted_at.asc())
        .all()
    )
    priority_lane = [r for r in active_requests if r.is_priority]
    regular_lane = [r for r in active_requests if not r.is_priority]
    return render_template(
        'admin/dashboard.html',
        priority_lane=priority_lane,
        regular_lane=regular_lane,
        active_total=len(active_requests),
    )


@admin_bp.route('/history')
def history():
    query = PrintRequest.query.join(User, PrintRequest.customer_id == User.id)

    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    service_type = request.args.get('service_type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like)))
    if status in STATUSES:
        query = query.filter(PrintRequest.status == status)
    if service_type in SERVICE_TYPES:
        query = query.filter(PrintRequest.service_type == service_type)
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(PrintRequest.submitted_at >= df)
        except ValueError:
            flash('Ignored an invalid "from" date.', 'warning')
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(PrintRequest.submitted_at <= dt)
        except ValueError:
            flash('Ignored an invalid "to" date.', 'warning')

    results = query.order_by(PrintRequest.submitted_at.desc()).limit(300).all()

    return render_template(
        'admin/history.html',
        results=results,
        filters=request.args,
        statuses=STATUSES,
        service_types=SERVICE_TYPES,
    )


@admin_bp.route('/request/<int:request_id>', methods=['GET', 'POST'])
def request_detail(request_id):
    print_request = PrintRequest.query.get_or_404(request_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'accept':
            completion_date_str = request.form.get('completion_date', '')
            admin_notes = request.form.get('admin_notes', '').strip()
            try:
                completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Please provide a valid completion date.', 'danger')
                return redirect(url_for('admin.request_detail', request_id=request_id))

            print_request.status = 'in_queue'
            print_request.completion_date = completion_date
            print_request.admin_notes = admin_notes
            db.session.commit()

            notify_customer(
                print_request.customer,
                f'Your print request #{print_request.id} ({print_request.service_type_label}) is on queue. '
                f'Expected completion: {completion_date.strftime("%B %d, %Y")}.',
                print_request=print_request,
            )
            flash('Request accepted and customer notified.', 'success')

        elif action == 'complete':
            print_request.status = 'completed'
            db.session.commit()
            notify_customer(
                print_request.customer,
                f'Your print request #{print_request.id} ({print_request.service_type_label}) '
                f'is complete and ready for pickup!',
                print_request=print_request,
            )
            flash('Request marked as completed.', 'success')

        elif action == 'cancel':
            print_request.status = 'cancelled'
            db.session.commit()
            notify_customer(
                print_request.customer,
                f'Your print request #{print_request.id} was cancelled. Please contact the shop for details.',
                print_request=print_request,
            )
            flash('Request cancelled.', 'info')

        elif action == 'edit_details':
            errors = []
            service_type = print_request.service_type
            try:
                copies = int(request.form.get('copies', ''))
                if copies < 1:
                    raise ValueError
            except (TypeError, ValueError):
                copies = print_request.copies
                errors.append('Copies must be a positive whole number.')

            paper_size = request.form.get('paper_size', '').strip()
            page_count_raw = request.form.get('page_count', '').strip()
            is_colored = request.form.get('is_colored') == 'on'
            width_raw = request.form.get('width_ft', '').strip()
            height_raw = request.form.get('height_ft', '').strip()
            shirt_size = request.form.get('shirt_size', '').strip()
            shirt_color = request.form.get('shirt_color', '').strip()
            page_count = print_request.page_count
            width_ft = print_request.width_ft
            height_ft = print_request.height_ft

            if service_type in ('document_print', 'soft_bind', 'hard_bind', 'laminate'):
                if paper_size not in PAPER_SIZES:
                    errors.append('Choose a valid paper size.')
            if service_type in ('document_print', 'soft_bind', 'hard_bind'):
                try:
                    page_count = int(page_count_raw)
                    if page_count < 1:
                        raise ValueError
                except (TypeError, ValueError):
                    errors.append('Page count must be a positive whole number.')
            if service_type == 'tarpaulin':
                try:
                    width_ft = float(width_raw)
                    height_ft = float(height_raw)
                    if not math.isfinite(width_ft) or not math.isfinite(height_ft) or width_ft <= 0 or height_ft <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors.append('Enter valid positive tarpaulin dimensions.')
                is_colored = True
            if service_type == 'shirt_print':
                if shirt_size not in SHIRT_SIZES:
                    errors.append('Choose a valid shirt size.')
                if len(shirt_color) > 30:
                    errors.append('Shirt color must be 30 characters or fewer.')

            if errors:
                for error in errors:
                    flash(error, 'danger')
                return render_template(
                    'admin/request_detail.html', req=print_request,
                    paper_sizes=PAPER_SIZES, shirt_sizes=SHIRT_SIZES,
                )

            print_request.copies = copies
            if service_type in ('document_print', 'soft_bind', 'hard_bind', 'laminate'):
                print_request.paper_size = paper_size
            if service_type in ('document_print', 'soft_bind', 'hard_bind'):
                print_request.page_count = page_count
                print_request.is_colored = is_colored
            elif service_type == 'tarpaulin':
                print_request.width_ft = width_ft
                print_request.height_ft = height_ft
            elif service_type == 'shirt_print':
                print_request.shirt_size = shirt_size
                print_request.shirt_color = shirt_color or None
                print_request.is_colored = is_colored

            print_request.estimated_price = calculate_price(
                service_type=service_type,
                copies=print_request.copies,
                is_colored=print_request.is_colored,
                page_count=print_request.page_count,
                width_ft=print_request.width_ft,
                height_ft=print_request.height_ft,
                is_urgent=print_request.is_urgent,
            )
            db.session.commit()
            notify_customer(
                print_request.customer,
                f'The shop updated the details for request #{print_request.id}. '
                f'New specifications: {print_request.display_specs}; '
                f'{print_request.copies} copies; estimated total {print_request.formatted_price}.',
                print_request=print_request,
            )
            flash('Request details updated and customer notified.', 'success')

        return redirect(url_for('admin.request_detail', request_id=request_id))

    return render_template(
        'admin/request_detail.html', req=print_request,
        paper_sizes=PAPER_SIZES, shirt_sizes=SHIRT_SIZES,
    )


@admin_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
