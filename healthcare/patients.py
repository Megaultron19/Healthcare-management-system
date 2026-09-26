from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .extensions import db
from .forms import PatientForm
from .models import Appointment, MedicalRecord, Patient, Prescription
from .utils import admin_required, fill_model

bp = Blueprint("patients", __name__, url_prefix="/patients")


def get_patient(patient_id):
    return db.session.get(Patient, patient_id) or abort(404)


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = db.select(Patient).order_by(Patient.last_name, Patient.first_name)
    if q:
        like = f"%{q}%"
        conditions = [
            Patient.first_name.ilike(like),
            Patient.last_name.ilike(like),
            Patient.phone.ilike(like),
            Patient.email.ilike(like),
            (Patient.first_name + " " + Patient.last_name).ilike(like),
        ]
        if q.lstrip("#").isdigit():
            conditions.append(Patient.id == int(q.lstrip("#")))
        query = query.where(db.or_(*conditions))
    page = db.paginate(query, per_page=current_app.config["PER_PAGE"], error_out=False)
    return render_template("patients/list.html", page=page, q=q)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient()
        fill_model(patient, form)
        db.session.add(patient)
        db.session.commit()
        flash(f"Patient {patient.full_name} added.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))
    return render_template("form.html", form=form, title="Add patient", cancel_url=url_for("patients.index"))


@bp.route("/<int:patient_id>")
@login_required
def detail(patient_id):
    patient = get_patient(patient_id)
    appointments = db.session.scalars(
        db.select(Appointment)
        .filter_by(patient_id=patient.id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
    ).all()
    records = db.session.scalars(
        db.select(MedicalRecord)
        .filter_by(patient_id=patient.id)
        .order_by(MedicalRecord.visit_date.desc(), MedicalRecord.id.desc())
    ).all()
    prescriptions = db.session.scalars(
        db.select(Prescription)
        .filter_by(patient_id=patient.id)
        .order_by(Prescription.prescribed_on.desc(), Prescription.id.desc())
    ).all()
    return render_template(
        "patients/detail.html",
        patient=patient,
        appointments=appointments,
        records=records,
        prescriptions=prescriptions,
    )


@bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit(patient_id):
    patient = get_patient(patient_id)
    form = PatientForm(obj=patient)
    if form.validate_on_submit():
        fill_model(patient, form)
        db.session.commit()
        flash("Patient details saved.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))
    return render_template(
        "form.html",
        form=form,
        title=f"Edit patient — {patient.full_name}",
        cancel_url=url_for("patients.detail", patient_id=patient.id),
    )


@bp.route("/<int:patient_id>/delete", methods=["POST"])
@admin_required
def delete(patient_id):
    patient = get_patient(patient_id)
    name = patient.full_name
    db.session.delete(patient)
    db.session.commit()
    flash(f"Patient {name} and all of their records were deleted.", "success")
    return redirect(url_for("patients.index"))
