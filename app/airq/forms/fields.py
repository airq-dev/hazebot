import pytz

from wtforms import DateTimeField
from wtforms.widgets import Input

from airq.lib.clock import now


class LocalDateTimeInput(Input):
    input_type = "datetime-local"


class LocalDateTimeField(DateTimeField):
    widget = LocalDateTimeInput()

    def __init__(
        self, *args, timezone="America/Los_Angeles", render_kw: dict = None, **kwargs
    ):
        render_kw = render_kw or {}
        render_kw["max"] = kwargs.get("default", now()).strftime("%Y-%m-%dT%H:%M")
        kwargs["format"] = "%Y-%m-%dT%H:%M"
        super().__init__(*args, render_kw=render_kw, **kwargs)
        self._timezone = timezone

    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data:
            self.data = pytz.timezone(self._timezone).localize(self.data)
