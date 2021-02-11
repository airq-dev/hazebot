import codecs
import csv
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
from werkzeug import Response

from airq.decorators import admin_required
from airq.forms import BulkClientUploadForm
from airq.forms import BulkSMSForm
from airq.forms import LoginForm
from airq.forms import SMSForm
from airq.lib.clock import now
from airq.lib.clock import timestamp
from airq.lib.sms import coerce_phone_number
from airq.lib.sms import is_valid_phone_number
from airq.models.clients import Client
from airq.models.clients import ClientIdentifierType
from airq.models.events import Event
from airq.models.zipcodes import Zipcode
from airq.models.users import User
from airq.tasks import bulk_send


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
    return render_template("admin/login.html", title="Sign In", form=form)


@login_required
def logout() -> Response:
    logout_user()
    return redirect(url_for("login"))


@admin_required
def admin_summary() -> str:
    return render_template(
        "admin/admin.html",
        title="Admin",
        summary={
            "Total Alerts Sent": Client.query.get_total_num_sends(),
            "Total Subscribed Clients": Client.query.get_total_num_subscriptions(),
            "Total New Clients": Client.query.get_total_new(),
            "Total Clients": Client.query.filter_phones().count(),
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
        "admin/bulk_sms.html",
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
    return render_template("admin/sms.html", form=form)


@admin_required
def upload_users():
    form = BulkClientUploadForm()
    if form.validate_on_submit():
        buffer = form.csv_file.data.stream
        reader = csv.DictReader(codecs.iterdecode(buffer, "utf-8"))
        headers = reader.fieldnames
        if "phone_number" not in headers or "zipcode" not in headers:
            flash(
                "You must upload a CSV with a column titled 'phone_number' and a column titled 'zipcode'"
            )
        else:
            num_created = 0
            num_duplicates = 0
            all_errors = []
            for i, row in enumerate(reader, start=1):
                errors = []

                zipcode = Zipcode.query.get_by_zipcode(row["zipcode"].strip())
                if zipcode is None:
                    errors.append(f"Row {i}: {row['zipcode']} is not a valid zipcode")

                phone_number = coerce_phone_number(row["phone_number"].strip())
                if not is_valid_phone_number(phone_number):
                    errors.append(
                        f"Row {i}: {row['phone_number']} is not a valid US phone number"
                    )

                if errors:
                    all_errors.extend(errors)
                else:
                    client, was_created = Client.query.get_or_create(
                        phone_number, ClientIdentifierType.PHONE_NUMBER
                    )
                    if was_created:
                        client.update_subscription(zipcode)
                        num_created += 1
                    else:
                        num_duplicates += 1

            if num_created:
                flash(f"Created {num_created} users")
            if num_duplicates:
                flash(
                    f"Skipped {num_duplicates} phone numbers because they're already in the system"
                )
            for error in all_errors:
                flash(error)

        return redirect(url_for("upload_users"))

    return render_template("admin/bulk_upload.html", form=form)
