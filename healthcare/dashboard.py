from datetime import timedelta

from flask import Blueprint, render_template
from flask_login import login_required

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
    stats = {
        "patients": _count(db.select(db.func.count(Patient.id))),
        "doctors": _count(db.select(db.func.count(Doctor.id)).filter(Doctor.active.is_(True))),
        "today": _count(
            db.select(db.func.count(Appointment.id)).filter(
                Appointment.date == today, Appointment.status != "Cancelled"
            )
        ),
        "prescriptions": _count(db.select(db.func.count(Prescription.id)).filter(Prescription.status == "Active")),
    }
    todays = db.session.scalars(
        db.select(Appointment).filter(Appointment.date == today).order_by(Appointment.time)
    ).all()
    upcoming = db.session.scalars(
        db.select(Appointment)
        .filter(
            Appointment.date > today,
            Appointment.date <= today + timedelta(days=7),
            Appointment.status == "Scheduled",
        )
        .order_by(Appointment.date, Appointment.time)
        .limit(8)
    ).all()
    follow_ups = db.session.scalars(
        db.select(MedicalRecord)
        .filter(MedicalRecord.follow_up_date >= today, MedicalRecord.follow_up_date <= today + timedelta(days=14))
        .order_by(MedicalRecord.follow_up_date)
        .limit(8)
    ).all()
    recent_patients = db.session.scalars(db.select(Patient).order_by(Patient.created_at.desc()).limit(5)).all()
    return render_template(
        "dashboard.html",
        stats=stats,
        todays=todays,
        upcoming=upcoming,
        follow_ups=follow_ups,
        recent_patients=recent_patients,
    )
