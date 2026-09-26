"""What the signed-in user may see.

Admins and staff see everything. A doctor sees only their own patients (anyone they have an
appointment, visit record or prescription with) and only their own appointments, visits and
prescriptions.
"""
from flask import abort
from flask_login import current_user

from .extensions import db
from .models import Appointment, MedicalRecord, Prescription


def doctor_scope():
    """The doctor id the current user is limited to, or None for full access."""
    if current_user.is_authenticated and current_user.is_doctor:
        return current_user.doctor_id or -1  # a doctor login without a linked profile sees nothing
    return None


def my_patient_ids(doctor_id):
    """Subquery of patient ids linked to a doctor through any appointment, visit or prescription."""
    return db.union(
        db.select(Appointment.patient_id).filter(Appointment.doctor_id == doctor_id),
        db.select(MedicalRecord.patient_id).filter(MedicalRecord.doctor_id == doctor_id),
        db.select(Prescription.patient_id).filter(Prescription.doctor_id == doctor_id),
    )


def scope_patients(query, patient_id_column):
    """Limit a query to the current doctor's patients (no-op for admin/staff)."""
    doctor_id = doctor_scope()
    if doctor_id is None:
        return query
    return query.filter(patient_id_column.in_(my_patient_ids(doctor_id)))


def scope_doctor(query, doctor_id_column):
    """Limit a query to rows belonging to the current doctor (no-op for admin/staff)."""
    doctor_id = doctor_scope()
    if doctor_id is None:
        return query
    return query.filter(doctor_id_column == doctor_id)


def ensure_patient_access(patient):
    """404 if a doctor tries to open someone else's patient (404 so ids don't leak)."""
    doctor_id = doctor_scope()
    if doctor_id is None:
        return
    in_scope = db.session.scalar(
        db.select(db.literal(True)).where(db.literal(patient.id).in_(my_patient_ids(doctor_id)))
    )
    if not in_scope:
        abort(404)


def ensure_own(obj):
    """404 unless the appointment/record/prescription belongs to the current doctor."""
    doctor_id = doctor_scope()
    if doctor_id is not None and obj.doctor_id != doctor_id:
        abort(404)


def staff_only():
    """403 for doctor accounts on clinic-management pages."""
    if doctor_scope() is not None:
        abort(403)
