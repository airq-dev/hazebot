"""
Generate vcards (in English and Spanish)
and put them in Nginx.

You'll need to install vobject
"""
import os
import vobject


ROOT = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/nginx/html/public/"
)


def gen_vcard(locale: str, number: str):
    v_card = vobject.vCard()
    v_card.add("FN").value = "Hazebot"
    v_card.add("TEL")
    v_card.tel.value = number
    v_card.tel.type_param = "text"
    v_card.add("PHOTO")
    v_card.photo.type_param = "JPEG"
    v_card.photo.encoding_param = "b"
    with open(ROOT + "icon.jpg", "rb") as f:
        v_card.photo.value = f.read()

    outfile = ROOT + "vcard/" + locale + ".vcf"
    with open(outfile, "w") as writer:
        writer.write(v_card.serialize())


if __name__ == "__main__":
    gen_vcard("en", "+12627472332")
    gen_vcard("es", "+17732506640")
