import os
import re
from datetime import time, timedelta

import pytest

from healthcare import create_app
from healthcare.cli import seed_demo_data
from healthcare.extensions import db
from healthcare.models import Appointment, Doctor, MedicalRecord, Patient, Prescription, User
from healthcare.utils import local_today

ADMIN = {"email": "admin@example.com", "password": "admin-pass-123"}
STAFF = {"email": "staff@example.com", "password": "staff-pass-123"}


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": os.environ.get("TEST_DATABASE_URL", "sqlite://"),
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded(app):
    for data, role, name in ((ADMIN, "admin", "Ada Admin"), (STAFF, "staff", "Sam Staff")):
        user = User(name=name, email=data["email"], role=role)
        user.set_password(data["password"])
        db.session.add(user)
    db.session.commit()
    seed_demo_data()
    return app


def login(client, creds):
    return client.post("/login", data=creds, follow_redirects=True)


@pytest.fixture
def admin(seeded):
    client = seeded.test_client()
    login(client, ADMIN)
    return client


@pytest.fixture
def staff(seeded):
    client = seeded.test_client()
    login(client, STAFF)
    return client


# ---- Auth -------------------------------------------------------------------


def test_first_run_redirects_to_setup_and_creates_admin(app):
    client = app.test_client()
    assert client.get("/").headers["Location"].startswith("/login")
    assert client.get("/login").headers["Location"] == "/setup"
    resp = client.post(
        "/setup",
        data={"name": "Owner", "email": "Owner@Clinic.com", "password": "longpassword", "confirm": "longpassword"},
        follow_redirects=True,
    )
    assert b"Welcome back, Owner" in resp.data
    user = db.session.scalar(db.select(User))
    assert user.email == "owner@clinic.com" and user.is_admin
    # Setup is disabled once a user exists.
    assert client.get("/setup").headers["Location"] == "/login"


def test_login_rejects_bad_password_and_inactive_users(seeded):
    client = seeded.test_client()
    assert b"Incorrect email or password" in login(client, {"email": ADMIN["email"], "password": "wrong"}).data
    staff_user = db.session.scalar(db.select(User).filter_by(email=STAFF["email"]))
    staff_user.active = False
    db.session.commit()
    assert b"deactivated" in login(client, STAFF).data


def test_login_ignores_external_next(seeded):
    client = seeded.test_client()
    for target in ("https://evil.example", "//evil.example", "/\\evil.example"):
        resp = client.post(f"/login?next={target}", data=ADMIN)
        assert resp.headers["Location"] == "/"
        client.post("/logout")


def test_pages_require_login(seeded):
    client = seeded.test_client()
    for url in ("/", "/patients/", "/doctors/", "/appointments/", "/prescriptions", "/users"):
        assert client.get(url).status_code == 302


def test_staff_cannot_use_admin_features(staff):
    patient = db.session.scalar(db.select(Patient))
    assert staff.get("/users").status_code == 403
    assert staff.get("/doctors/new").status_code == 403
    assert staff.post(f"/patients/{patient.id}/delete").status_code == 403
    assert db.session.get(Patient, patient.id) is not None


def test_csrf_is_enforced_when_enabled(seeded):
    seeded.config["WTF_CSRF_ENABLED"] = True
    client = seeded.test_client()
    assert client.post("/login", data=ADMIN).status_code == 400


# ---- Every page renders ----------------------------------------------------


def test_all_pages_render(admin):
    patient = db.session.scalar(db.select(Patient).filter_by(first_name="Alice"))
    doctor = db.session.scalar(db.select(Doctor))
    record = db.session.scalar(db.select(MedicalRecord))
    rx = db.session.scalar(db.select(Prescription))
    appt = db.session.scalar(db.select(Appointment))
    user = db.session.scalar(db.select(User))
    urls = [
        "/", "/patients/", "/patients/?q=coo", f"/patients/?q=%23{patient.id}", "/patients/new",
        f"/patients/{patient.id}", f"/patients/{patient.id}/edit",
        "/doctors/", "/doctors/?q=cardio", "/doctors/new", f"/doctors/{doctor.id}", f"/doctors/{doctor.id}/edit",
        "/appointments/", f"/appointments/?date={local_today().isoformat()}&status=Scheduled&doctor_id={doctor.id}&q=a",
        "/appointments/?date=not-a-date", "/appointments/new", f"/appointments/{appt.id}/edit",
        f"/patients/{patient.id}/records/new", f"/records/{record.id}/edit",
        "/prescriptions", "/prescriptions?status=Active&q=nitro",
        f"/patients/{patient.id}/prescriptions/new", f"/patients/{patient.id}/prescriptions/new?record_id={record.id}",
        f"/prescriptions/{rx.id}/edit", "/users", "/users/new", f"/users/{user.id}/edit", "/account/password",
    ]
    for url in urls:
        resp = admin.get(url)
        assert resp.status_code == 200, url
    assert admin.get("/patients/99999").status_code == 404
    assert b"Penicillin" in admin.get(f"/patients/{patient.id}").data


def test_dashboard_shows_todays_schedule(admin):
    html = admin.get("/").data.decode()
    assert "Alice Cooper" in html and "Angina follow-up" in html
    assert re.search(r'stat-value">\s*8\s*<', html)  # 8 demo patients


# ---- Patients ----------------------------------------------------------------


def test_patient_crud(admin):
    resp = admin.post(
        "/patients/new",
        data={"first_name": " Nina ", "last_name": "Patel", "date_of_birth": "1990-02-01", "gender": "Female",
              "blood_group": "", "phone": "555-9999", "email": ""},
        follow_redirects=True,
    )
    assert b"Patient Nina Patel added" in resp.data
    nina = db.session.scalar(db.select(Patient).filter_by(last_name="Patel"))
    assert nina.first_name == "Nina" and nina.blood_group is None and nina.email is None

    admin.post(f"/patients/{nina.id}/edit",
               data={"first_name": "Nina", "last_name": "Patel-Shah", "date_of_birth": "1990-02-01", "gender": "Female",
                     "blood_group": "O+", "allergies": "Pollen"})
    db.session.refresh(nina)
    assert nina.last_name == "Patel-Shah" and nina.blood_group == "O+"

    assert b"Patel-Shah" in admin.get("/patients/?q=nina patel").data or b"Patel-Shah" in admin.get("/patients/?q=Patel").data
    admin.post(f"/patients/{nina.id}/delete")
    assert db.session.get(Patient, nina.id) is None


def test_patient_validation(admin):
    future = (local_today() + timedelta(days=2)).isoformat()
    resp = admin.post("/patients/new", data={"first_name": "", "last_name": "X", "date_of_birth": future, "gender": "Male"})
    assert resp.status_code == 200
    assert b"This field is required" in resp.data and b"can&#39;t be in the future" in resp.data
    resp = admin.post("/patients/new", data={"first_name": "A", "last_name": "B", "date_of_birth": "2000-01-01", "gender": "Robot"})
    assert b"Not a valid choice" in resp.data


def test_deleting_patient_removes_their_records(admin):
    alice = db.session.scalar(db.select(Patient).filter_by(first_name="Alice"))
    pid = alice.id
    admin.post(f"/patients/{pid}/delete")
    db.session.expire_all()
    for model in (Appointment, MedicalRecord, Prescription):
        assert db.session.scalar(db.select(db.func.count(model.id)).filter_by(patient_id=pid)) == 0


# ---- Doctors -----------------------------------------------------------------


def test_doctor_crud_and_protected_delete(admin):
    admin.post("/doctors/new", data={"first_name": "Kim", "last_name": "Lee", "specialization": "ENT", "active": "y"})
    kim = db.session.scalar(db.select(Doctor).filter_by(last_name="Lee"))
    assert kim.active
    # Duplicate email is rejected.
    smith = db.session.scalar(db.select(Doctor).filter_by(last_name="Smith"))
    resp = admin.post(f"/doctors/{kim.id}/edit", data={"first_name": "Kim", "last_name": "Lee", "specialization": "ENT", "email": smith.email.upper()})
    assert b"Another doctor already uses this email" in resp.data
    # Deactivate (checkbox absent = False).
    admin.post(f"/doctors/{kim.id}/edit", data={"first_name": "Kim", "last_name": "Lee", "specialization": "ENT"})
    db.session.refresh(kim)
    assert not kim.active
    # A doctor with history can't be deleted; a fresh one can.
    resp = admin.post(f"/doctors/{smith.id}/delete", follow_redirects=True)
    assert b"can&#39;t be deleted" in resp.data and db.session.get(Doctor, smith.id)
    admin.post(f"/doctors/{kim.id}/delete")
    assert db.session.get(Doctor, kim.id) is None


def test_inactive_doctor_hidden_from_booking(admin):
    smith = db.session.scalar(db.select(Doctor).filter_by(last_name="Smith"))
    smith.active = False
    db.session.commit()
    assert b"Dr. John Smith" not in admin.get("/appointments/new").data


# ---- Appointments ------------------------------------------------------------


def _appt_data(patient, doctor, day, at="09:00", status="Scheduled"):
    return {"patient_id": patient.id, "doctor_id": doctor.id, "date": day.isoformat(), "time": at, "status": status, "reason": "Check"}


def test_book_edit_and_status_change(staff):
    frank = db.session.scalar(db.select(Patient).filter_by(first_name="Frank"))
    brown = db.session.scalar(db.select(Doctor).filter_by(last_name="Brown"))
    day = local_today() + timedelta(days=20)
    resp = staff.post("/appointments/new", data=_appt_data(frank, brown, day, "10:00"), follow_redirects=True)
    assert b"Appointment booked" in resp.data
    appt = db.session.scalar(db.select(Appointment).filter_by(patient_id=frank.id, doctor_id=brown.id))
    assert appt.time == time(10, 0)

    staff.post(f"/appointments/{appt.id}/edit", data=_appt_data(frank, brown, day, "11:30"))
    db.session.refresh(appt)
    assert appt.time == time(11, 30)

    resp = staff.post(f"/appointments/{appt.id}/status", data={"status": "Completed", "next": "/appointments/?status=Completed"})
    assert resp.headers["Location"] == "/appointments/?status=Completed"
    db.session.refresh(appt)
    assert appt.status == "Completed"
    assert staff.post(f"/appointments/{appt.id}/status", data={"status": "Bogus"}).status_code == 400


def test_double_booking_is_blocked(staff):
    alice = db.session.scalar(db.select(Patient).filter_by(first_name="Alice"))
    frank = db.session.scalar(db.select(Patient).filter_by(first_name="Frank"))
    smith = db.session.scalar(db.select(Doctor).filter_by(last_name="Smith"))
    taylor = db.session.scalar(db.select(Doctor).filter_by(last_name="Taylor"))
    today = local_today()
    # Smith already sees Alice today at 09:00.
    resp = staff.post("/appointments/new", data=_appt_data(frank, smith, today, "09:00"))
    assert b"This doctor already has an appointment" in resp.data
    resp = staff.post("/appointments/new", data=_appt_data(alice, taylor, today, "09:00"))
    assert b"This patient already has an appointment" in resp.data
    # Booking a cancelled slot record is fine.
    resp = staff.post("/appointments/new", data=_appt_data(frank, smith, today, "09:00", status="Cancelled"))
    assert resp.status_code == 302


def test_admin_deletes_appointment(admin):
    appt = db.session.scalar(db.select(Appointment))
    admin.post(f"/appointments/{appt.id}/delete")
    assert db.session.get(Appointment, appt.id) is None


# ---- Records & prescriptions -------------------------------------------------


def test_visit_record_and_prescription_flow(staff):
    frank = db.session.scalar(db.select(Patient).filter_by(first_name="Frank"))
    taylor = db.session.scalar(db.select(Doctor).filter_by(last_name="Taylor"))
    today = local_today()
    resp = staff.post(f"/patients/{frank.id}/records/new", data={
        "doctor_id": taylor.id, "visit_date": today.isoformat(), "diagnosis": "Hypertension",
        "blood_pressure": "150/95", "follow_up_date": (today + timedelta(days=5)).isoformat(),
    })
    assert resp.headers["Location"].endswith(f"/patients/{frank.id}#records")
    record = db.session.scalar(db.select(MedicalRecord).filter_by(patient_id=frank.id))
    assert record.diagnosis == "Hypertension"

    bad = staff.post(f"/patients/{frank.id}/records/new", data={
        "doctor_id": taylor.id, "visit_date": today.isoformat(), "follow_up_date": (today - timedelta(days=1)).isoformat()})
    assert b"Follow-up can&#39;t be before the visit" in bad.data

    staff.post(f"/patients/{frank.id}/prescriptions/new?record_id={record.id}", data={
        "doctor_id": taylor.id, "prescribed_on": today.isoformat(), "medication": "Amlodipine",
        "dosage": "5mg", "frequency": "Once daily", "status": "Active", "refills": ""})
    rx = db.session.scalar(db.select(Prescription).filter_by(medication="Amlodipine"))
    assert rx.record_id == record.id and rx.refills == 0

    staff.post(f"/prescriptions/{rx.id}/edit", data={
        "doctor_id": taylor.id, "prescribed_on": today.isoformat(), "medication": "Amlodipine",
        "dosage": "10mg", "frequency": "Once daily", "status": "Discontinued", "refills": "1"})
    db.session.refresh(rx)
    assert rx.dosage == "10mg" and rx.status == "Discontinued"

    page = staff.get(f"/patients/{frank.id}").data
    assert b"Hypertension" in page and b"Amlodipine" in page and b"150/95" in page


def test_prescription_record_must_belong_to_patient(staff):
    alice = db.session.scalar(db.select(Patient).filter_by(first_name="Alice"))
    frank = db.session.scalar(db.select(Patient).filter_by(first_name="Frank"))
    alice_record = db.session.scalar(db.select(MedicalRecord).filter_by(patient_id=alice.id))
    assert staff.get(f"/patients/{frank.id}/prescriptions/new?record_id={alice_record.id}").status_code == 400


def test_deleting_record_keeps_prescription(admin):
    record = db.session.scalar(db.select(MedicalRecord).where(MedicalRecord.prescriptions.any()))
    rx_id = record.prescriptions[0].id
    admin.post(f"/records/{record.id}/delete")
    db.session.expire_all()
    rx = db.session.get(Prescription, rx_id)
    assert rx is not None and rx.record_id is None


# ---- Users -----------------------------------------------------------------


def test_user_management(admin):
    resp = admin.post("/users/new", data={"name": "Rita", "email": "rita@example.com", "role": "staff", "active": "y", "password": ""})
    assert b"A password is required" in resp.data
    admin.post("/users/new", data={"name": "Rita", "email": "Rita@Example.com", "role": "staff", "active": "y", "password": "rita-pass-1"})
    rita = db.session.scalar(db.select(User).filter_by(email="rita@example.com"))
    assert rita and not rita.is_admin
    resp = admin.post("/users/new", data={"name": "Dup", "email": "rita@example.com", "role": "staff", "password": "whatever-123"})
    assert b"already exists" in resp.data

    me = db.session.scalar(db.select(User).filter_by(email=ADMIN["email"]))
    resp = admin.post(f"/users/{me.id}/edit", data={"name": me.name, "email": me.email, "role": "staff", "active": "y"}, follow_redirects=True)
    assert b"can&#39;t remove your own admin access" in resp.data
    db.session.refresh(me)
    assert me.is_admin


def test_change_password(staff):
    resp = staff.post("/account/password", data={"current": "nope", "password": "new-password-1", "confirm": "new-password-1"})
    assert b"Current password is incorrect" in resp.data
    staff.post("/account/password", data={"current": STAFF["password"], "password": "new-password-1", "confirm": "new-password-1"})
    user = db.session.scalar(db.select(User).filter_by(email=STAFF["email"]))
    assert user.check_password("new-password-1")


# ---- Config ----------------------------------------------------------------


def test_database_url_normalisation(monkeypatch):
    from healthcare import _database_url

    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db?sslmode=require")
    assert _database_url() == "postgresql+psycopg2://u:p@host/db?sslmode=require"
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host/db")
    assert _database_url() == "postgresql+psycopg2://u:p@host/db"


def test_production_without_config_shows_setup_page(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    for var in ("SECRET_KEY", "DATABASE_URL", "POSTGRES_URL"):
        monkeypatch.delenv(var, raising=False)
    resp = create_app().test_client().get("/patients/")
    assert resp.status_code == 500
    assert b"SECRET_KEY is not set" in resp.data and b"DATABASE_URL must be set" in resp.data


def test_unreachable_database_shows_setup_page(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:secret@127.0.0.1:1/db")
    resp = create_app().test_client().get("/")
    assert resp.status_code == 500
    assert b"Could not connect to the database" in resp.data and b"secret" not in resp.data


def test_production_requires_database_url(monkeypatch):
    from healthcare import _database_url

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    with pytest.raises(RuntimeError):
        _database_url()
