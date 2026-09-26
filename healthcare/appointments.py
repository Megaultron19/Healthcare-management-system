from datetime import date

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .forms import AppointmentForm, doctor_choices, patient_choices
from .models import APPOINTMENT_STATUSES, Appointment, Doctor, Patient
from .utils import admin_required, fill_model, local_today, safe_url

bp = Blueprint("appointments", __name__, url_prefix="/appointments")


def get_appointment(appointment_id):
    return db.session.get(Appointment, appointment_id) or abort(404)


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _slot_conflict(form, exclude_id=None):
    """Return an error message if the doctor or patient is already booked at that slot."""
    if form.status.data != "Scheduled":
        return None
    base = db.select(Appointment).filter(
        Appointment.date == form.date.data,
        Appointment.time == form.time.data,
        Appointment.status == "Scheduled",
    )
    if exclude_id:
        base = base.filter(Appointment.id != exclude_id)
    if db.session.scalar(base.filter(Appointment.doctor_id == form.doctor_id.data).limit(1)):
        return "This doctor already has an appointment at that date and time."
    if db.session.scalar(base.filter(Appointment.patient_id == form.patient_id.data).limit(1)):
        return "This patient already has an appointment at that date and time."
    return None


def _set_choices(form, current_doctor_id=None):
    form.patient_id.choices = patient_choices()
    form.doctor_id.choices = doctor_choices(include_id=current_doctor_id)


@bp.route("/")
@login_required
def index():
    day = _parse_date(request.args.get("date"))
    status = request.args.get("status", "")
    doctor_id = request.args.get("doctor_id", type=int)
    q = request.args.get("q", "").strip()

    query = db.select(Appointment).join(Appointment.patient).join(Appointment.doctor)
    if day:
        query = query.filter(Appointment.date == day)
    if status in APPOINTMENT_STATUSES:
        query = query.filter(Appointment.status == status)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(like),
                Patient.last_name.ilike(like),
                (Patient.first_name + " " + Patient.last_name).ilike(like),
                Appointment.reason.ilike(like),
            )
        )
    query = query.order_by(Appointment.date.desc(), Appointment.time.desc())
    page = db.paginate(query, per_page=current_app.config["PER_PAGE"], error_out=False)
    doctors = db.session.scalars(db.select(Doctor).order_by(Doctor.last_name, Doctor.first_name)).all()
    return render_template(
        "appointments/list.html",
        page=page,
        doctors=doctors,
        statuses=APPOINTMENT_STATUSES,
        filters={"date": day.isoformat() if day else "", "status": status, "doctor_id": doctor_id, "q": q},
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = AppointmentForm()
    _set_choices(form)
    back = safe_url(request.args.get("next"), url_for("appointments.index"))
    if request.method == "GET":
        form.patient_id.data = request.args.get("patient_id", type=int)
        form.doctor_id.data = request.args.get("doctor_id", type=int)
        form.date.data = _parse_date(request.args.get("date")) or local_today()
    if not form.patient_id.choices or not form.doctor_id.choices:
        flash("Add at least one patient and one active doctor before booking appointments.", "error")
        return redirect(url_for("appointments.index"))
    if form.validate_on_submit():
        conflict = _slot_conflict(form)
        if conflict:
            form.time.errors.append(conflict)
        else:
            appointment = Appointment()
            fill_model(appointment, form)
            db.session.add(appointment)
            db.session.commit()
            flash("Appointment booked.", "success")
            return redirect(back)
    return render_template("form.html", form=form, title="Book appointment", cancel_url=back)


@bp.route("/<int:appointment_id>/edit", methods=["GET", "POST"])
@login_required
def edit(appointment_id):
    appointment = get_appointment(appointment_id)
    form = AppointmentForm(obj=appointment)
    _set_choices(form, current_doctor_id=appointment.doctor_id)
    back = safe_url(request.args.get("next"), url_for("appointments.index"))
    if form.validate_on_submit():
        conflict = _slot_conflict(form, exclude_id=appointment.id)
        if conflict:
            form.time.errors.append(conflict)
        else:
            fill_model(appointment, form)
            db.session.commit()
            flash("Appointment updated.", "success")
            return redirect(back)
    return render_template("form.html", form=form, title="Edit appointment", cancel_url=back)


@bp.route("/<int:appointment_id>/status", methods=["POST"])
@login_required
def set_status(appointment_id):
    appointment = get_appointment(appointment_id)
    status = request.form.get("status")
    if status not in APPOINTMENT_STATUSES:
        abort(400)
    appointment.status = status
    db.session.commit()
    flash(f"Appointment marked as {status}.", "success")
    return redirect(safe_url(request.form.get("next"), url_for("appointments.index")))


@bp.route("/<int:appointment_id>/delete", methods=["POST"])
@admin_required
def delete(appointment_id):
    appointment = get_appointment(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash("Appointment deleted.", "success")
    return redirect(safe_url(request.form.get("next"), url_for("appointments.index")))
