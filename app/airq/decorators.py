import functools

from flask import abort
from flask_login import current_user
from flask_login import login_required


def admin_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            abort(403, description="Permission denied")
        return func(*args, **kwargs)

    return login_required(decorated_view)
