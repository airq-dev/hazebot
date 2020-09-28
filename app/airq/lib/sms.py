import phonenumbers


def coerce_phone_number(phone_number: str) -> str:
    if len(phone_number) == 10:
        phone_number = "1" + phone_number
    if len(phone_number) == 11:
        phone_number = "+" + phone_number
    return phone_number


def is_valid_phone_number(phone_number: str) -> bool:
    number_obj = phonenumbers.parse(phone_number, region="US")
    if not number_obj:
        return False
    return phonenumbers.is_valid_number(number_obj)
