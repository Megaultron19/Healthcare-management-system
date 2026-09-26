from datetime import timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from .access import scope_doctor, scope_patients
from .extensions import db
from .models import Appointment, Doctor, MedicalRecord, Patient, Prescription
from .utils import local_today

bp = Blueprint("dashboard", __name__)


def _count(query):
    return db.session.scalar(query)


@bp.route("/")
@login_required
def index():
    today = local_today()
    appts = scope_doctor(db.select(Appointment), Appointment.doctor_id)
    stats = {
        "patients": _count(scope_patients(db.select(db.func.count(Patient.id)), Patient.id)),
        "today": _count(
            appts.with_only_columns(db.func.count(Appointment.id)).filter(
                Appointment.date == today, Appointment.status != "Cancelled"
            )
        ),
        "prescriptions": _count(
            scope_doctor(db.select(db.func.count(Prescription.id)), Prescription.doctor_id).filter(
                Prescription.status == "Active"
            )
        ),
    }
    if current_user.is_doctor:
        stats["visits"] = _count(
            scope_doctor(db.select(db.func.count(MedicalRecord.id)), MedicalRecord.doctor_id).filter(
                MedicalRecord.visit_date >= today - timedelta(days=30)
            )
        )
    else:
        stats["doctors"] = _count(db.select(db.func.count(Doctor.id)).filter(Doctor.active.is_(True)))
    todays = db.session.scalars(appts.filter(Appointment.date == today).order_by(Appointment.time)).all()
    upcoming = db.session.scalars(
        appts.filter(
            Appointment.date > today,
            Appointment.date <= today + timedelta(days=7),
            Appointment.status == "Scheduled",
        )
        .order_by(Appointment.date, Appointment.time)
        .limit(8)
    ).all()
    follow_ups = db.session.scalars(
        scope_doctor(db.select(MedicalRecord), MedicalRecord.doctor_id)
        .filter(MedicalRecord.follow_up_date >= today, MedicalRecord.follow_up_date <= today + timedelta(days=14))
        .order_by(MedicalRecord.follow_up_date)
        .limit(8)
    ).all()
    recent_patients = db.session.scalars(
        scope_patients(db.select(Patient), Patient.id).order_by(Patient.created_at.desc()).limit(5)
    ).all()
    return render_template(
        "dashboard.html",
        stats=stats,
        todays=todays,
        upcoming=upcoming,
        follow_ups=follow_ups,
        recent_patients=recent_patients,
    )
