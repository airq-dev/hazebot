import typing

from wtforms import validators

from airq.models.clients import Client


class PhoneNumberValidator:
    def __init__(self, message: typing.Optional[str] = None):
        self.message = message

    def __call__(self, form, field):
        if not field.data or not isinstance(field.data, str):
            return

        data = field.data.strip()
        if not data:
            return

        client = Client.query.get_by_phone_number(data)
        if client:
            return

        if self.message is None:
            message = field.gettext(f"Couldn't find a user with number {data}")
        else:
            message = self.message

        field.errors[:] = []
        raise validators.StopValidation(message)
