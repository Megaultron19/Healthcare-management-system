# Clinic Manager — Healthcare Management System

A complete web application for clinics to manage **patients, doctors, appointments, visit records and prescriptions**. Built with Python (Flask) and SQLAlchemy, it runs on **Neon Postgres** in the cloud or a local **SQLite** file with zero setup, and deploys to **Vercel** in a few clicks.

## Features

**Dashboard**
- Live counts: patients, today's appointments, active doctors, active prescriptions
- Today's schedule with one-click “Mark done”
- Appointments for the next 7 days
- Follow-ups due in the next 14 days, with one-click booking

**Patients**
- Add, edit, delete and search (name, phone, email or `#ID`)
- Full profile: demographics, blood group, allergies (highlighted in red), emergency contact, notes
- Per-patient tabs for visits, prescriptions and appointments

**Visit records**
- Complaint, symptoms, diagnosis, treatment and notes
- Vitals: BP, temperature, pulse, SpO₂, weight
- Follow-up date, and prescribing directly from a visit

**Prescriptions**
- Medication, dosage, frequency, duration, quantity and refills
- Status: Active, Completed or Discontinued
- Clinic-wide list with search and status filter

**Appointments**
- Book, reschedule and cancel
- Status: Scheduled, Completed, Cancelled or No-Show, changeable straight from the list
- Double-booking protection for both doctors and patients
- Filter by date, doctor, status or patient name

**Doctors**
- Profiles with specialization, department and contact details
- Upcoming appointments and recent visits
- Deactivate a doctor to hide them from booking while keeping their history

**Users and security**
- Sign-in with hashed passwords
- Three roles:
  - **Admin** manages doctors and users and can delete records
  - **Staff** handles day-to-day work across the clinic
  - **Doctor** sees only their own patients, appointments, visits and prescriptions
- CSRF protection on every form
- Secure cookies in production
- First-run setup page that creates the initial admin

**Responsive UI**
- Works on desktop, tablet and phone, with a collapsible sidebar on small screens

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3, Flask-Login, Flask-WTF |
| Database | SQLAlchemy 2 with **Neon Postgres** (online) or **SQLite** (local) |
| Frontend | Server-rendered Jinja templates with custom CSS and a little vanilla JS (no build step) |
| Hosting | Vercel (Python runtime) |

## Run it locally

```bash
git clone https://github.com/Megaultron19/healthcare-management-system.git
cd healthcare-management-system
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

flask --app app seed               # optional: load demo doctors, patients and appointments
python app.py                      # open http://localhost:5000
```

With no `DATABASE_URL` set, data is stored in `instance/healthcare.db` (SQLite). The first time you open the app it asks you to **create the administrator account**.

To use your Neon database locally instead, set `DATABASE_URL` before running:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@ep-xxxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require"
```

## Deploy to Vercel with Neon

1. **Push this repository to GitHub**, then in Vercel choose **Add New → Project** and import it. Vercel detects Flask automatically, so no build settings are needed.
2. **Create the database:** in the Vercel project open **Storage → Create Database → Neon (Serverless Postgres)** and connect it to the project. This adds `DATABASE_URL` to the project's environment variables. Alternatively, create a project at [neon.tech](https://neon.tech) and add its **pooled** connection string as `DATABASE_URL` yourself.
3. **Add a secret key:** under **Settings → Environment Variables**, add `SECRET_KEY`. Generate one with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
4. **Optional variables:**
   - `APP_NAME`: your clinic or brand name, shown in the sidebar and page titles
   - `TIMEZONE`: the clinic's timezone, e.g. `Asia/Kolkata`. Set this because Vercel servers run on UTC, and "today" should mean the clinic's today.
5. **Deploy** (or redeploy after adding variables), open the site and create your admin account.

Tables are created automatically on first start. To load demo data into Neon, run `flask --app app seed` locally with `DATABASE_URL` pointing at Neon.

## Doctor logins

1. Sign in as an admin and open a doctor's page under **Doctors**.
2. Click **Create login**, then set the email and password. You can also do this from **Users → Add user**, choosing the Doctor role and the doctor profile.
3. When that doctor signs in, they see only:
   - their own patients: anyone with an appointment, visit or prescription with them, including that patient's full history so they have the clinical context
   - their own appointments and prescriptions
   - a dashboard for their day

Doctors can record visits, prescribe and book follow-ups for their own patients. They can't add new patients, see other doctors' patients, or change other doctors' entries. Reception or an admin adds new patients and books their first appointment with the doctor.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | In production | Signs sessions and CSRF tokens. The app refuses to start on Vercel without it. |
| `DATABASE_URL` | In production | Postgres connection string (`POSTGRES_URL` is also accepted). Falls back to SQLite locally. |
| `APP_NAME` | No | Display name. Default: `Clinic Manager`. |
| `TIMEZONE` | No | IANA timezone, e.g. `Asia/Kolkata`. Default: the server's local time. |

See `.env.example`.

## Management commands

```bash
flask --app app init-db        # create tables (also happens automatically on start)
flask --app app create-admin   # create an admin from the terminal
flask --app app seed           # load demo data into an empty database
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                   # runs against in-memory SQLite
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/test_db pytest   # against Postgres
```

## Project structure

```
app.py                  # entry point (used by Vercel and `python app.py`)
healthcare/
  __init__.py           # app factory and configuration
  models.py             # database tables
  forms.py              # form definitions and validation
  auth.py               # sign-in, setup, users, password change
  dashboard.py, patients.py, doctors.py, appointments.py, records.py
  cli.py                # init-db / create-admin / seed commands
templates/              # HTML pages
public/static/          # CSS, JS, favicon (served by Vercel's CDN)
tests/                  # automated tests
```

## Before using with real patients

This software handles medical information. Before using it with real patient data or selling it, make sure the deployment meets the health-data laws of the market you sell into, for example HIPAA (US), GDPR (EU/UK) or India's DPDP Act. Typical requirements are a signed data-processing agreement with your hosting and database providers, regular backups, access logging, and strong passwords for every user.

## Author

**Harshit Singh** · GitHub: [Megaultron19](https://github.com/Megaultron19) · harshitkatiyar2003@gmail.com
