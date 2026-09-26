from datetime import date, time, timedelta

import click

from .extensions import db
from .models import Appointment, Doctor, MedicalRecord, Patient, Prescription, User
from .utils import local_today


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables (safe to run repeatedly)."""
        db.create_all()
        click.echo("Database tables are ready.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create an administrator account."""
        email = email.strip().lower()
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        if db.session.scalar(db.select(User).filter_by(email=email)):
            raise click.ClickException(f"A user with email {email} already exists.")
        user = User(name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator {email} created.")

    @app.cli.command("seed")
    def seed():
        """Load demo doctors, patients, visits, prescriptions and appointments."""
        if db.session.scalar(db.select(db.func.count(Patient.id))):
            raise click.ClickException("The database already has patients; refusing to add demo data.")
        seed_demo_data()
        click.echo("Demo data loaded.")


def seed_demo_data():
    today = local_today()
    d = lambda days: today + timedelta(days=days)  # noqa: E731

    doctors = [
        Doctor(first_name="John", last_name="Smith", specialization="Cardiology", department="Cardiac Care", phone="555-0101", email="john.smith@example.com"),
        Doctor(first_name="Sarah", last_name="Johnson", specialization="Pediatrics", department="Pediatric Care", phone="555-0102", email="sarah.johnson@example.com"),
        Doctor(first_name="Michael", last_name="Brown", specialization="Orthopedics", department="Orthopedic Surgery", phone="555-0103", email="michael.brown@example.com"),
        Doctor(first_name="Emily", last_name="Davis", specialization="Dermatology", department="Dermatology", phone="555-0104", email="emily.davis@example.com"),
        Doctor(first_name="Robert", last_name="Wilson", specialization="Neurology", department="Neurology", phone="555-0105", email="robert.wilson@example.com"),
        Doctor(first_name="Lisa", last_name="Anderson", specialization="Gynecology", department="Women's Health", phone="555-0106", email="lisa.anderson@example.com"),
        Doctor(first_name="David", last_name="Taylor", specialization="General Medicine", department="General Medicine", phone="555-0107", email="david.taylor@example.com"),
        Doctor(first_name="Jennifer", last_name="Thomas", specialization="Psychiatry", department="Mental Health", phone="555-0108", email="jennifer.thomas@example.com"),
    ]
    smith, johnson, brown, davis, wilson, anderson, taylor, thomas = doctors

    patients = [
        Patient(first_name="Alice", last_name="Cooper", date_of_birth=date(1985, 3, 15), gender="Female", blood_group="A+", phone="555-1001", email="alice.cooper@example.com", address="123 Main St", allergies="Penicillin", emergency_contact_name="Bob Cooper", emergency_contact_phone="555-2001"),
        Patient(first_name="Leo", last_name="Williams", date_of_birth=date(2016, 7, 22), gender="Male", blood_group="O-", phone="555-1002", address="456 Oak Ave", emergency_contact_name="Mary Williams", emergency_contact_phone="555-2002"),
        Patient(first_name="Catherine", last_name="Jones", date_of_birth=date(1958, 11, 8), gender="Female", blood_group="B+", phone="555-1003", address="789 Pine Rd", allergies="Shellfish", emergency_contact_name="Tom Jones", emergency_contact_phone="555-2003"),
        Patient(first_name="Daniel", last_name="Miller", date_of_birth=date(1995, 1, 30), gender="Male", blood_group="AB+", phone="555-1004", address="321 Elm St", allergies="Peanuts", emergency_contact_name="Susan Miller", emergency_contact_phone="555-2004"),
        Patient(first_name="Eva", last_name="Moore", date_of_birth=date(1988, 9, 12), gender="Female", blood_group="A-", phone="555-1005", address="654 Maple Dr", allergies="Latex", emergency_contact_name="John Moore", emergency_contact_phone="555-2005"),
        Patient(first_name="Grace", last_name="Lewis", date_of_birth=date(1983, 12, 3), gender="Female", blood_group="B-", phone="555-1007", address="147 Birch Ave", allergies="Sulfa drugs", emergency_contact_name="Mark Lewis", emergency_contact_phone="555-2007"),
        Patient(first_name="Henry", last_name="Walker", date_of_birth=date(1991, 4, 18), gender="Male", blood_group="AB-", phone="555-1008", address="258 Spruce St", emergency_contact_name="Linda Walker", emergency_contact_phone="555-2008"),
        Patient(first_name="Frank", last_name="Clark", date_of_birth=date(1970, 5, 25), gender="Male", blood_group="O+", phone="555-1006", address="987 Cedar Ln", emergency_contact_name="Helen Clark", emergency_contact_phone="555-2006"),
    ]
    alice, leo, catherine, daniel, eva, grace, henry, frank = patients
    db.session.add_all(doctors + patients)
    db.session.flush()

    records = [
        MedicalRecord(patient=alice, doctor=smith, visit_date=d(-40), chief_complaint="Chest pain", diagnosis="Stable angina", symptoms="Chest tightness, shortness of breath on exertion", treatment="Nitroglycerin as needed, lifestyle changes", blood_pressure="140/90", temperature="98.6", pulse="85", oxygen_saturation="98", follow_up_date=d(5)),
        MedicalRecord(patient=leo, doctor=johnson, visit_date=d(-20), chief_complaint="Fever and cough", diagnosis="Upper respiratory infection", symptoms="Fever, persistent cough, runny nose", treatment="Rest, fluids, antibiotics", blood_pressure="100/65", temperature="101.2", pulse="105", oxygen_saturation="97", follow_up_date=d(-6)),
        MedicalRecord(patient=catherine, doctor=brown, visit_date=d(-30), chief_complaint="Knee pain", diagnosis="Osteoarthritis", symptoms="Joint pain and morning stiffness", treatment="Physical therapy, anti-inflammatory medication", blood_pressure="130/85", temperature="98.4", pulse="78", oxygen_saturation="99", follow_up_date=d(10)),
        MedicalRecord(patient=daniel, doctor=davis, visit_date=d(-12), chief_complaint="Skin rash", diagnosis="Eczema", symptoms="Itchy, red patches on arms", treatment="Topical steroid, moisturisers", blood_pressure="122/80", temperature="98.8", pulse="72", oxygen_saturation="98", follow_up_date=d(12)),
        MedicalRecord(patient=eva, doctor=wilson, visit_date=d(-8), chief_complaint="Headaches", diagnosis="Migraine", symptoms="Severe headaches with light sensitivity", treatment="Triptan at onset, trigger diary", blood_pressure="118/76", temperature="98.2", pulse="68", oxygen_saturation="99"),
        MedicalRecord(patient=grace, doctor=taylor, visit_date=d(-15), chief_complaint="Fatigue", diagnosis="Iron deficiency anaemia", symptoms="Weakness, fatigue, pale skin", treatment="Iron supplements, dietary changes", blood_pressure="110/70", temperature="98.3", pulse="88", oxygen_saturation="97", follow_up_date=d(3)),
        MedicalRecord(patient=henry, doctor=thomas, visit_date=d(-5), chief_complaint="Anxiety", diagnosis="Generalised anxiety disorder", symptoms="Worry, restlessness, poor sleep", treatment="CBT referral, relaxation techniques", blood_pressure="125/80", temperature="98.5", pulse="82", oxygen_saturation="98", follow_up_date=d(9)),
    ]
    db.session.add_all(records)
    db.session.flush()
    r_alice, r_leo, r_cath, r_daniel, r_eva, r_grace, _ = records

    db.session.add_all([
        Prescription(patient=alice, doctor=smith, record=r_alice, prescribed_on=r_alice.visit_date, medication="Nitroglycerin", dosage="0.4mg", frequency="As needed", duration="30 days", instructions="Dissolve under the tongue at onset of chest pain", quantity=30, refills=2),
        Prescription(patient=leo, doctor=johnson, record=r_leo, prescribed_on=r_leo.visit_date, medication="Azithromycin suspension", dosage="10mg/kg", frequency="Once daily", duration="3 days", instructions="Complete the full course", quantity=1, refills=0, status="Completed"),
        Prescription(patient=catherine, doctor=brown, record=r_cath, prescribed_on=r_cath.visit_date, medication="Ibuprofen", dosage="400mg", frequency="3 times daily", duration="14 days", instructions="Take with food", quantity=42, refills=1),
        Prescription(patient=daniel, doctor=davis, record=r_daniel, prescribed_on=r_daniel.visit_date, medication="Hydrocortisone cream", dosage="1%", frequency="Twice daily", duration="14 days", instructions="Apply a thin layer to affected areas", quantity=1, refills=0),
        Prescription(patient=eva, doctor=wilson, record=r_eva, prescribed_on=r_eva.visit_date, medication="Sumatriptan", dosage="50mg", frequency="As needed", duration="30 days", instructions="Take at onset of migraine; max 2 per day", quantity=9, refills=2),
        Prescription(patient=grace, doctor=taylor, record=r_grace, prescribed_on=r_grace.visit_date, medication="Ferrous sulfate", dosage="325mg", frequency="Once daily", duration="90 days", instructions="Take on an empty stomach", quantity=90, refills=2),
    ])

    db.session.add_all([
        Appointment(patient=alice, doctor=smith, date=today, time=time(9, 0), reason="Angina follow-up"),
        Appointment(patient=eva, doctor=wilson, date=today, time=time(10, 30), reason="Migraine review"),
        Appointment(patient=frank, doctor=taylor, date=today, time=time(11, 15), reason="Annual physical"),
        Appointment(patient=leo, doctor=johnson, date=today, time=time(14, 0), reason="Post-infection check"),
        Appointment(patient=grace, doctor=taylor, date=d(3), time=time(8, 30), reason="Iron levels review"),
        Appointment(patient=eva, doctor=anderson, date=d(4), time=time(13, 0), reason="Annual women's health exam"),
        Appointment(patient=henry, doctor=thomas, date=d(9), time=time(15, 15), reason="Therapy progress review"),
        Appointment(patient=catherine, doctor=brown, date=d(10), time=time(11, 0), reason="Physiotherapy assessment"),
        Appointment(patient=daniel, doctor=davis, date=d(-12), time=time(16, 30), reason="Skin rash", status="Completed"),
        Appointment(patient=henry, doctor=taylor, date=d(-3), time=time(10, 0), reason="General check-up", status="No-Show"),
        Appointment(patient=catherine, doctor=smith, date=d(-2), time=time(9, 30), reason="Cardiac consultation", status="Cancelled"),
    ])
    db.session.commit()
