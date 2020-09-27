from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField
from wtforms.validators import DataRequired

from airq.forms.fields import LocalDateTimeField
from airq.forms.validators import PhoneNumberValidator


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired()],
        render_kw={"placeholder": "Email"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
        render_kw={"placeholder": "Password"},
    )
    submit = SubmitField("Submit")


class BulkSMSForm(FlaskForm):
    message = TextAreaField(
        "Message", validators=[DataRequired()], render_kw={"cols": 50, "rows": 10}
    )
    last_active_at = LocalDateTimeField("Last Active At", validators=[DataRequired()])
    submit_btn = SubmitField("Submit")


class SMSForm(FlaskForm):
    message = TextAreaField(
        "Message", validators=[DataRequired()], render_kw={"cols": 50, "rows": 10}
    )
    phone_number = StringField(
        "Phone Number", validators=[PhoneNumberValidator(), DataRequired()]
    )
    submit_btn = SubmitField("Submit")


class BulkClientUploadForm(FlaskForm):
    csv_file = FileField(
        "CSV File", validators=[DataRequired()], render_kw={"accept": ".csv"}
    )
    submit_btn = SubmitField("Upload")
