"""
Generate vcards (in English and Spanish)
and put them in Nginx.

You'll need to install vobject
"""
import os
import vobject


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def gen_vcard(locale: str, number: str):
    v_card = vobject.vCard()
    v_card.add("FN").value = "Hazebot"
    v_card.add("TEL")
    v_card.tel.value = number
    v_card.tel.type_param = "text"

    outfile = ROOT + "/nginx/html/vcard/" + locale + ".vcf"
    with open(outfile, "w") as writer:
        writer.write(v_card.serialize())


if __name__ == "__main__":
    gen_vcard("en", "+12627472332")
    gen_vcard("es", "+17732506640")
