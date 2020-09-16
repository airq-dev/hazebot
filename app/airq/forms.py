from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[validators.DataRequired()],
        render_kw={"placeholder": "Email"},
    )
    password = PasswordField(
        "Password",
        validators=[validators.DataRequired()],
        render_kw={"placeholder": "Password"},
    )
    submit = SubmitField("Submit")
