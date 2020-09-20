import typing

from flask import flash
from flask import jsonify
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
from airq.config import csrf
from airq.decorators import admin_required
from airq.forms import BulkSMSForm
from airq.forms import LoginForm
from airq.forms import SMSForm
from airq.lib.clock import now
from airq.lib.clock import timestamp
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.events import Event
from airq.models.requests import Request
from airq.models.users import User
from airq.tasks import bulk_send


def healthcheck() -> str:
    return "OK"


@csrf.exempt
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
        return redirect(url_for("admin_summary"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("login"))
        login_user(user, remember=True)
        return redirect(url_for("admin_summary"))
    return render_template("login.html", title="Sign In", form=form)


@login_required
def logout() -> Response:
    logout_user()
    return redirect(url_for("login"))


@admin_required
def admin_summary() -> str:
    return render_template(
        "admin.html",
        title="Admin",
        summary={
            "Total Alerts Sent": Client.query.get_total_num_sends(),
            "Total Subscribed Clients": Client.query.get_total_num_subscriptions(),
            "Total Clients": Client.query.filter_phones().count(),
            "Total Zipcode Requests": Request.query.get_total_count(),
        },
        activity_counts=Client.query.get_activity_counts(),
        event_stats=Event.query.get_stats(),
    )


@admin_required
def admin_stats():
    last_active_at = request.args.get("last_active_at")
    if not last_active_at:
        return Response(status=400)
    num_clients = Client.query.filter_inactive_since(last_active_at).count()
    return jsonify({"num_clients": num_clients})


@admin_required
def admin_bulk_sms():
    if not current_user.can_send_sms:
        return redirect(url_for("admin_summary"))
    form = BulkSMSForm(last_active_at=now())
    if form.validate_on_submit():
        bulk_send.delay(form.data["message"], form.data["last_active_at"].timestamp())
        flash("Sent!")
        return redirect(url_for("admin_summary"))
    return render_template(
        "bulk_sms.html",
        form=form,
        num_inactive=Client.query.filter_inactive_since(timestamp()).count(),
    )


@admin_required
def admin_sms():
    if not current_user.can_send_sms:
        return redirect(url_for("admin_summary"))
    form = SMSForm()
    if form.validate_on_submit():
        client = Client.query.get_by_phone_number(form.data["phone_number"])
        client.send_message(form.data["message"])
        flash("Sent!")
        return redirect(url_for("admin_summary"))
    return render_template("sms.html", form=form)
