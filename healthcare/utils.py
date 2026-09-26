import os
from datetime import date, datetime
from functools import wraps
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def fill_model(obj, form, exclude=("csrf_token",)):
    """Copy form data onto a model, storing blank strings as NULL."""
    for name, field in form._fields.items():
        if name in exclude or not hasattr(obj, name):
            continue
        value = field.data
        if isinstance(value, str):
            value = value.strip() or None
        setattr(obj, name, value)


def safe_url(target, fallback):
    """Only allow redirects to paths on this site; otherwise use the fallback."""
    if target and target.startswith("/") and not target.startswith(("//", "/\\")) and not urlsplit(target).netloc:
        return target
    return fallback


def local_today():
    """Today's date in the clinic's timezone (TIMEZONE env var), falling back to server local time."""
    tz_name = os.environ.get("TIMEZONE")
    if tz_name:
        return datetime.now(ZoneInfo(tz_name)).date()
    return date.today()
