from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .forms import ChangePasswordForm, LoginForm, SetupForm, UserForm, doctor_link_choices
from .models import Doctor, User
from .utils import admin_required, fill_model, safe_url

bp = Blueprint("auth", __name__)


def _no_users():
    return db.session.scalar(db.select(db.func.count(User.id))) == 0


@bp.route("/login", methods=["GET", "POST"])
def login():
    if _no_users():
        return redirect(url_for("auth.setup"))
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).filter_by(email=form.email.data.strip().lower()))
        if user and user.check_password(form.password.data):
            if not user.active:
                flash("This account has been deactivated. Contact your administrator.", "error")
            else:
                login_user(user, remember=form.remember.data)
                return redirect(safe_url(request.args.get("next"), url_for("dashboard.index")))
        else:
            flash("Incorrect email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """First-run page: create the initial administrator. Disabled once any user exists."""
    if not _no_users():
        return redirect(url_for("auth.login"))
    form = SetupForm()
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(), role="admin")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome! Your administrator account is ready.", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth/setup.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            form.current.errors.append("Current password is incorrect.")
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("form.html", form=form, title="Change password", cancel_url=url_for("dashboard.index"))


@bp.route("/users")
@admin_required
def users():
    all_users = db.session.scalars(db.select(User).order_by(User.name)).all()
    return render_template("users/list.html", users=all_users)


def _email_taken(email, exclude_id=None):
    user = db.session.scalar(db.select(User).filter_by(email=email))
    return user is not None and user.id != exclude_id


def _doctor_link_error(form, exclude_id=None):
    """Validate the doctor profile link; returns an error message or None."""
    if form.role.data != "doctor":
        return None
    if not form.doctor_id.data or not db.session.get(Doctor, form.doctor_id.data):
        return "Choose the doctor profile this login belongs to."
    owner = db.session.scalar(db.select(User).filter_by(doctor_id=form.doctor_id.data))
    if owner and owner.id != exclude_id:
        return f"This doctor already has a login ({owner.email})."
    return None


def _save_user(user, form, email):
    fill_model(user, form, exclude=("csrf_token", "doctor_id"))
    user.email = email
    user.doctor_id = form.doctor_id.data if form.role.data == "doctor" else None


@bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = UserForm()
    form.doctor_id.choices = doctor_link_choices()
    form.password.description = "At least 8 characters."
    if request.method == "GET" and request.args.get("doctor_id", type=int):
        doctor = db.session.get(Doctor, request.args.get("doctor_id", type=int))
        if doctor:
            form.role.data, form.doctor_id.data = "doctor", doctor.id
            form.name.data, form.email.data = f"{doctor.first_name} {doctor.last_name}", doctor.email
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        link_error = _doctor_link_error(form)
        if not form.password.data:
            form.password.errors.append("A password is required for new users.")
        elif _email_taken(email):
            form.email.errors.append("A user with this email already exists.")
        elif link_error:
            form.doctor_id.errors.append(link_error)
        else:
            user = User()
            _save_user(user, form, email)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f"User {user.name} created.", "success")
            return redirect(url_for("auth.users"))
    return render_template("form.html", form=form, title="Add user", cancel_url=url_for("auth.users"))


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id) or abort(404)
    form = UserForm(obj=user)
    form.doctor_id.choices = doctor_link_choices()
    if request.method == "GET":
        form.doctor_id.data = user.doctor_id or 0
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        is_self = user.id == current_user.id
        link_error = _doctor_link_error(form, exclude_id=user.id)
        if _email_taken(email, exclude_id=user.id):
            form.email.errors.append("A user with this email already exists.")
        elif is_self and (form.role.data != "admin" or not form.active.data):
            flash("You can't remove your own admin access or deactivate yourself.", "error")
        elif link_error:
            form.doctor_id.errors.append(link_error)
        else:
            _save_user(user, form, email)
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            flash(f"User {user.name} updated.", "success")
            return redirect(url_for("auth.users"))
    return render_template("form.html", form=form, title=f"Edit user — {user.name}", cancel_url=url_for("auth.users"))
