from flask_babel import gettext

from airq.commands.base import MessageResponse
from airq.commands.base import RegexCommand
from airq.commands.base import SMSCommand
from airq.lib.client_preferences import ClientPreferencesRegistry
from airq.lib.client_preferences import InvalidPrefValue
from airq.models.events import EventType


class ListPrefs(RegexCommand):
    pattern = r"^3[\.\)]?$"

    def handle(self) -> MessageResponse:
        response = MessageResponse()
        response.write(gettext("Which preference do you want to set?"))
        for letter, pref in ClientPreferencesRegistry.iter_with_letters():
            response.write(f"{letter} - {pref.display_name}: {pref.description}")
        self.client.log_event(EventType.LIST_PREFS)
        return response


class RequestSetPref(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.has_recent_last_event_of_type(EventType.LIST_PREFS)

    def handle(self) -> MessageResponse:
        letter = self.user_input.strip()
        pref = ClientPreferencesRegistry.get_by_letter(letter)
        if pref is None:
            return MessageResponse(
                body=gettext(
                    "Hmm, %(input)s doesn't seem to be a valid choice. Please try again.",
                    input=self.user_input[:20],
                )
            )

        self.client.log_event(EventType.SET_PREF_REQUEST, pref_name=pref.name)

        response = MessageResponse()
        response.write(pref.get_prompt())
        formatted_value = pref.format_value(getattr(self.client, pref.name))
        response.write(gettext("Current: %(value)s", value=formatted_value))

        return response


class SetPref(SMSCommand):
    def should_handle(self) -> bool:
        return self.client.has_recent_last_event_of_type(EventType.SET_PREF_REQUEST)

    def handle(self) -> MessageResponse:
        event = self.client.get_last_client_event()
        if not event or event.type_code != EventType.SET_PREF_REQUEST:
            return MessageResponse(
                body=gettext("Hmm, looks like something went wrong. Try again?")
            )

        pref_name = event.validate()["pref_name"]
        pref = ClientPreferencesRegistry.get_by_name(pref_name)

        try:
            value = pref.set_from_user_input(self.client, self.user_input)
        except InvalidPrefValue as e:
            return MessageResponse(body=str(e))

        self.client.log_event(EventType.SET_PREF, pref_name=pref.name, pref_value=value)

        return MessageResponse(
            body=gettext(
                "Your %(pref)s is now %(value)s",
                pref=pref.display_name,
                value=pref.format_value(value),
            )
        )
