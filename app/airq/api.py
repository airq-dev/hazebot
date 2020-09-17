import typing

from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import logout_user
from twilio.twiml.messaging_response import MessagingResponse
from werkzeug import Response

from airq import commands
from airq.decorators import admin_required
from airq.forms import LoginForm
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.users import User


def healthcheck() -> str:
    return "OK"


def sms_reply() -> str:
    resp = MessagingResponse()
    zipcode = request.values.get("Body", "").strip()
    phone_number = request.values.get("From", "").strip()
    message = commands.handle_command(
        zipcode, phone_number, ClientIdentifierType.PHONE_NUMBER
    )
    resp.message(message)
    return str(resp)


def test_command() -> str:
    command = request.args.get("command", "").strip()
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return commands.handle_command(command, ip, ClientIdentifierType.IP)


def login() -> typing.Union[Response, str]:
    if current_user.is_authenticated:
        # TODO: Redirect to the admin page.
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("login"))
        login_user(user, remember=True)
        # TODO: Redirect to the admin page.
        return redirect("/")
    return render_template("login.html", title="Sign In", form=form)


@login_required
def logout() -> Response:
    logout_user()
    return redirect(url_for("login"))


@admin_required
def admin() -> str:
    summary_metrics = {
        "num_sent": Client.get_total_num_sends(),
        "num_subscribed_clients": Client.get_total_num_subscriptions(),
    }
    activity_counts = Client.get_inactive_counts()
    return render_template("admin.html", title="Admin", stats=stats)
