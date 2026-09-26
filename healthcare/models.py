from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

GENDERS = ["Male", "Female", "Other"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
PRESCRIPTION_STATUSES = ["Active", "Completed", "Discontinued"]
ROLES = ["admin", "staff"]


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    active = db.Column(db.Boolean, nullable=False, default=True)

    @property
    def is_active(self):
        return self.active

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Doctor(TimestampMixin, db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False, index=True)
    specialization = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    appointments = db.relationship("Appointment", back_populates="doctor")
    records = db.relationship("MedicalRecord", back_populates="doctor")
    prescriptions = db.relationship("Prescription", back_populates="doctor")

    @property
    def full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"


class Patient(TimestampMixin, db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    blood_group = db.Column(db.String(5))
    allergies = db.Column(db.Text)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)

    appointments = db.relationship(
        "Appointment", back_populates="patient", cascade="all, delete-orphan"
    )
    records = db.relationship(
        "MedicalRecord", back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions = db.relationship(
        "Prescription", back_populates="patient", cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class Appointment(TimestampMixin, db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Scheduled")
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")


class MedicalRecord(TimestampMixin, db.Model):
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    visit_date = db.Column(db.Date, nullable=False, index=True)
    chief_complaint = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)
    blood_pressure = db.Column(db.String(20))
    temperature = db.Column(db.String(10))
    pulse = db.Column(db.String(10))
    oxygen_saturation = db.Column(db.String(10))
    weight = db.Column(db.String(10))
    follow_up_date = db.Column(db.Date)

    patient = db.relationship("Patient", back_populates="records")
    doctor = db.relationship("Doctor", back_populates="records")
    prescriptions = db.relationship("Prescription", back_populates="record")


class Prescription(TimestampMixin, db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    record_id = db.Column(db.Integer, db.ForeignKey("medical_records.id", ondelete="SET NULL"))
    prescribed_on = db.Column(db.Date, nullable=False, default=date.today)
    medication = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100))
    instructions = db.Column(db.Text)
    quantity = db.Column(db.Integer)
    refills = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="Active")

    patient = db.relationship("Patient", back_populates="prescriptions")
    doctor = db.relationship("Doctor", back_populates="prescriptions")
    record = db.relationship("MedicalRecord", back_populates="prescriptions")
