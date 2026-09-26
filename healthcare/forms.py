from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import Email, EqualTo, InputRequired, Length, NumberRange, Optional, ValidationError

from .extensions import db
from .utils import local_today
from .models import (
    APPOINTMENT_STATUSES,
    BLOOD_GROUPS,
    GENDERS,
    PRESCRIPTION_STATUSES,
    ROLES,
    Doctor,
    Patient,
)


def doctor_choices(include_id=None):
    """Active doctors, plus the currently assigned one when editing an old record."""
    query = db.select(Doctor).order_by(Doctor.last_name, Doctor.first_name)
    doctors = [d for d in db.session.scalars(query) if d.active or d.id == include_id]
    return [(d.id, f"{d.full_name} — {d.specialization}") for d in doctors]


def patient_choices():
    query = db.select(Patient).order_by(Patient.last_name, Patient.first_name)
    return [(p.id, f"{p.full_name} (#{p.id})") for p in db.session.scalars(query)]


def _choices(values, blank=None):
    items = [(v, v) for v in values]
    return [("", blank)] + items if blank else items


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired(), Email()])
    password = PasswordField("Password", validators=[InputRequired()])
    remember = BooleanField("Keep me signed in")


class SetupForm(FlaskForm):
    name = StringField("Your name", validators=[InputRequired(), Length(max=100)])
    email = EmailField("Email", validators=[InputRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm password", validators=[InputRequired(), EqualTo("password", "Passwords must match.")])


class UserForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired(), Length(max=100)])
    email = EmailField("Email", validators=[InputRequired(), Email(), Length(max=120)])
    role = SelectField("Role", choices=[(r, r.title()) for r in ROLES])
    active = BooleanField("Account active", default=True)
    password = PasswordField(
        "Password", validators=[Optional(), Length(min=8, max=128)], description="Leave blank to keep the current password."
    )


class ChangePasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[InputRequired()])
    password = PasswordField("New password", validators=[InputRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm new password", validators=[InputRequired(), EqualTo("password", "Passwords must match.")])


class PatientForm(FlaskForm):
    first_name = StringField("First name", validators=[InputRequired(), Length(max=50)])
    last_name = StringField("Last name", validators=[InputRequired(), Length(max=50)])
    date_of_birth = DateField("Date of birth", validators=[InputRequired()])
    gender = SelectField("Gender", choices=_choices(GENDERS))
    blood_group = SelectField("Blood group", choices=_choices(BLOOD_GROUPS, blank="Unknown"), validators=[Optional()])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    email = EmailField("Email", validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField("Address", validators=[Optional()])
    allergies = TextAreaField("Allergies", validators=[Optional()])
    emergency_contact_name = StringField("Emergency contact name", validators=[Optional(), Length(max=100)])
    emergency_contact_phone = StringField("Emergency contact phone", validators=[Optional(), Length(max=20)])
    notes = TextAreaField("Notes", validators=[Optional()])

    def validate_date_of_birth(self, field):
        if field.data and field.data > local_today():
            raise ValidationError("Date of birth can't be in the future.")


class DoctorForm(FlaskForm):
    first_name = StringField("First name", validators=[InputRequired(), Length(max=50)])
    last_name = StringField("Last name", validators=[InputRequired(), Length(max=50)])
    specialization = StringField("Specialization", validators=[InputRequired(), Length(max=100)])
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    email = EmailField("Email", validators=[Optional(), Email(), Length(max=120)])
    active = BooleanField("Accepting appointments", default=True)


class AppointmentForm(FlaskForm):
    patient_id = SelectField("Patient", coerce=int, validators=[InputRequired()])
    doctor_id = SelectField("Doctor", coerce=int, validators=[InputRequired()])
    date = DateField("Date", validators=[InputRequired()])
    time = TimeField("Time", validators=[InputRequired()])
    status = SelectField("Status", choices=_choices(APPOINTMENT_STATUSES))
    reason = StringField("Reason for visit", validators=[Optional(), Length(max=500)])
    notes = TextAreaField("Notes", validators=[Optional()])


class MedicalRecordForm(FlaskForm):
    doctor_id = SelectField("Doctor", coerce=int, validators=[InputRequired()])
    visit_date = DateField("Visit date", validators=[InputRequired()])
    chief_complaint = TextAreaField("Chief complaint", validators=[Optional()])
    symptoms = TextAreaField("Symptoms", validators=[Optional()])
    diagnosis = TextAreaField("Diagnosis", validators=[Optional()])
    treatment = TextAreaField("Treatment provided", validators=[Optional()])
    blood_pressure = StringField("Blood pressure", validators=[Optional(), Length(max=20)], render_kw={"placeholder": "120/80"})
    temperature = StringField("Temperature (°F)", validators=[Optional(), Length(max=10)], render_kw={"placeholder": "98.6"})
    pulse = StringField("Pulse (bpm)", validators=[Optional(), Length(max=10)], render_kw={"placeholder": "72"})
    oxygen_saturation = StringField("SpO₂ (%)", validators=[Optional(), Length(max=10)], render_kw={"placeholder": "98"})
    weight = StringField("Weight (kg)", validators=[Optional(), Length(max=10)])
    follow_up_date = DateField("Follow-up date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])

    def validate_follow_up_date(self, field):
        if field.data and self.visit_date.data and field.data < self.visit_date.data:
            raise ValidationError("Follow-up can't be before the visit.")


class PrescriptionForm(FlaskForm):
    doctor_id = SelectField("Prescribing doctor", coerce=int, validators=[InputRequired()])
    prescribed_on = DateField("Date", validators=[InputRequired()])
    medication = StringField("Medication", validators=[InputRequired(), Length(max=200)])
    dosage = StringField("Dosage", validators=[InputRequired(), Length(max=100)], render_kw={"placeholder": "500mg"})
    frequency = StringField("Frequency", validators=[InputRequired(), Length(max=100)], render_kw={"placeholder": "Twice daily"})
    duration = StringField("Duration", validators=[Optional(), Length(max=100)], render_kw={"placeholder": "7 days"})
    quantity = IntegerField("Quantity", validators=[Optional(), NumberRange(min=0, max=100000)])
    refills = IntegerField("Refills", default=0, validators=[Optional(), NumberRange(min=0, max=100)])
    status = SelectField("Status", choices=_choices(PRESCRIPTION_STATUSES))
    instructions = TextAreaField("Instructions", validators=[Optional()])
