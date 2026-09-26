from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .forms import DoctorForm
from .models import Appointment, Doctor, MedicalRecord, Prescription
from .utils import admin_required, fill_model, local_today

bp = Blueprint("doctors", __name__, url_prefix="/doctors")


def get_doctor(doctor_id):
    return db.session.get(Doctor, doctor_id) or abort(404)


def _email_taken(email, exclude_id=None):
    if not email:
        return False
    doctor = db.session.scalar(db.select(Doctor).filter(db.func.lower(Doctor.email) == email.lower()))
    return doctor is not None and doctor.id != exclude_id


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = db.select(Doctor).order_by(Doctor.active.desc(), Doctor.last_name, Doctor.first_name)
    if q:
        like = f"%{q}%"
        query = query.where(
            db.or_(
                Doctor.first_name.ilike(like),
                Doctor.last_name.ilike(like),
                Doctor.specialization.ilike(like),
                Doctor.department.ilike(like),
            )
        )
    page = db.paginate(query, per_page=current_app.config["PER_PAGE"], error_out=False)
    return render_template("doctors/list.html", page=page, q=q)


@bp.route("/<int:doctor_id>")
@login_required
def detail(doctor_id):
    doctor = get_doctor(doctor_id)
    upcoming = db.session.scalars(
        db.select(Appointment)
        .filter(Appointment.doctor_id == doctor.id, Appointment.date >= local_today(), Appointment.status == "Scheduled")
        .order_by(Appointment.date, Appointment.time)
        .limit(20)
    ).all()
    recent = db.session.scalars(
        db.select(MedicalRecord)
        .filter_by(doctor_id=doctor.id)
        .order_by(MedicalRecord.visit_date.desc(), MedicalRecord.id.desc())
        .limit(10)
    ).all()
    return render_template("doctors/detail.html", doctor=doctor, upcoming=upcoming, recent=recent)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def new():
    form = DoctorForm()
    if form.validate_on_submit():
        if _email_taken(form.email.data):
            form.email.errors.append("Another doctor already uses this email.")
        else:
            doctor = Doctor()
            fill_model(doctor, form)
            db.session.add(doctor)
            db.session.commit()
            flash(f"{doctor.full_name} added.", "success")
            return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    return render_template("form.html", form=form, title="Add doctor", cancel_url=url_for("doctors.index"))


@bp.route("/<int:doctor_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(doctor_id):
    doctor = get_doctor(doctor_id)
    form = DoctorForm(obj=doctor)
    if form.validate_on_submit():
        if _email_taken(form.email.data, exclude_id=doctor.id):
            form.email.errors.append("Another doctor already uses this email.")
        else:
            fill_model(doctor, form)
            db.session.commit()
            flash("Doctor details saved.", "success")
            return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    return render_template(
        "form.html",
        form=form,
        title=f"Edit — {doctor.full_name}",
        cancel_url=url_for("doctors.detail", doctor_id=doctor.id),
    )


@bp.route("/<int:doctor_id>/delete", methods=["POST"])
@admin_required
def delete(doctor_id):
    doctor = get_doctor(doctor_id)
    linked = sum(
        db.session.scalar(db.select(db.func.count(model.id)).filter_by(doctor_id=doctor.id))
        for model in (Appointment, MedicalRecord, Prescription)
    )
    if linked:
        flash(
            f"{doctor.full_name} has {linked} linked appointment(s) or record(s) and can't be deleted. "
            "Edit the doctor and untick “Accepting appointments” instead.",
            "error",
        )
        return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    db.session.delete(doctor)
    db.session.commit()
    flash(f"{doctor.full_name} deleted.", "success")
    return redirect(url_for("doctors.index"))
