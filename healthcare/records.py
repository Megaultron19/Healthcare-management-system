"""Medical records (visits) and prescriptions — both belong to a patient."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required

from .access import ensure_own, scope_doctor
from .extensions import db
from .forms import MedicalRecordForm, PrescriptionForm, doctor_choices
from .models import PRESCRIPTION_STATUSES, MedicalRecord, Patient, Prescription
from .patients import get_patient
from .utils import admin_required, fill_model, local_today

bp = Blueprint("records", __name__)


def _patient_url(patient_id, tab):
    return url_for("patients.detail", patient_id=patient_id, _anchor=tab)


# ---- Medical records -------------------------------------------------------


@bp.route("/patients/<int:patient_id>/records/new", methods=["GET", "POST"])
@login_required
def new_record(patient_id):
    patient = get_patient(patient_id)
    form = MedicalRecordForm()
    form.doctor_id.choices = doctor_choices()
    if request.method == "GET":
        form.visit_date.data = local_today()
    if not form.doctor_id.choices:
        flash("Add an active doctor before recording visits.", "error")
        return redirect(_patient_url(patient.id, "records"))
    if form.validate_on_submit():
        record = MedicalRecord(patient_id=patient.id)
        fill_model(record, form)
        db.session.add(record)
        db.session.commit()
        flash("Visit record saved.", "success")
        return redirect(_patient_url(patient.id, "records"))
    return render_template(
        "form.html", form=form, title=f"New visit — {patient.full_name}", cancel_url=_patient_url(patient.id, "records")
    )


@bp.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(record_id):
    record = db.session.get(MedicalRecord, record_id) or abort(404)
    ensure_own(record)
    form = MedicalRecordForm(obj=record)
    form.doctor_id.choices = doctor_choices(include_id=record.doctor_id)
    if form.validate_on_submit():
        fill_model(record, form)
        db.session.commit()
        flash("Visit record updated.", "success")
        return redirect(_patient_url(record.patient_id, "records"))
    return render_template(
        "form.html",
        form=form,
        title=f"Edit visit — {record.patient.full_name}",
        cancel_url=_patient_url(record.patient_id, "records"),
    )


@bp.route("/records/<int:record_id>/delete", methods=["POST"])
@admin_required
def delete_record(record_id):
    record = db.session.get(MedicalRecord, record_id) or abort(404)
    patient_id = record.patient_id
    db.session.delete(record)
    db.session.commit()
    flash("Visit record deleted.", "success")
    return redirect(_patient_url(patient_id, "records"))


# ---- Prescriptions ---------------------------------------------------------


@bp.route("/prescriptions")
@login_required
def prescriptions():
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    query = scope_doctor(db.select(Prescription), Prescription.doctor_id).join(Prescription.patient)
    if status in PRESCRIPTION_STATUSES:
        query = query.filter(Prescription.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Prescription.medication.ilike(like),
                Patient.first_name.ilike(like),
                Patient.last_name.ilike(like),
                (Patient.first_name + " " + Patient.last_name).ilike(like),
            )
        )
    query = query.order_by(Prescription.prescribed_on.desc(), Prescription.id.desc())
    page = db.paginate(query, per_page=current_app.config["PER_PAGE"], error_out=False)
    return render_template(
        "prescriptions/list.html", page=page, statuses=PRESCRIPTION_STATUSES, filters={"status": status, "q": q}
    )


@bp.route("/patients/<int:patient_id>/prescriptions/new", methods=["GET", "POST"])
@login_required
def new_prescription(patient_id):
    patient = get_patient(patient_id)
    form = PrescriptionForm()
    form.doctor_id.choices = doctor_choices()
    record_id = request.args.get("record_id", type=int)
    record = db.session.get(MedicalRecord, record_id) if record_id else None
    if record and record.patient_id != patient.id:
        abort(400)
    if record:
        ensure_own(record)
    if request.method == "GET":
        form.prescribed_on.data = record.visit_date if record else local_today()
        if record:
            form.doctor_id.data = record.doctor_id
    if not form.doctor_id.choices:
        flash("Add an active doctor before writing prescriptions.", "error")
        return redirect(_patient_url(patient.id, "prescriptions"))
    if form.validate_on_submit():
        prescription = Prescription(patient_id=patient.id, record_id=record.id if record else None)
        fill_model(prescription, form)
        prescription.refills = prescription.refills or 0
        db.session.add(prescription)
        db.session.commit()
        flash(f"{prescription.medication} prescribed.", "success")
        return redirect(_patient_url(patient.id, "prescriptions"))
    return render_template(
        "form.html",
        form=form,
        title=f"New prescription — {patient.full_name}",
        cancel_url=_patient_url(patient.id, "prescriptions"),
    )


@bp.route("/prescriptions/<int:prescription_id>/edit", methods=["GET", "POST"])
@login_required
def edit_prescription(prescription_id):
    prescription = db.session.get(Prescription, prescription_id) or abort(404)
    ensure_own(prescription)
    form = PrescriptionForm(obj=prescription)
    form.doctor_id.choices = doctor_choices(include_id=prescription.doctor_id)
    if form.validate_on_submit():
        fill_model(prescription, form)
        prescription.refills = prescription.refills or 0
        db.session.commit()
        flash("Prescription updated.", "success")
        return redirect(_patient_url(prescription.patient_id, "prescriptions"))
    return render_template(
        "form.html",
        form=form,
        title=f"Edit prescription — {prescription.patient.full_name}",
        cancel_url=_patient_url(prescription.patient_id, "prescriptions"),
    )


@bp.route("/prescriptions/<int:prescription_id>/delete", methods=["POST"])
@admin_required
def delete_prescription(prescription_id):
    prescription = db.session.get(Prescription, prescription_id) or abort(404)
    patient_id = prescription.patient_id
    db.session.delete(prescription)
    db.session.commit()
    flash("Prescription deleted.", "success")
    return redirect(_patient_url(patient_id, "prescriptions"))
