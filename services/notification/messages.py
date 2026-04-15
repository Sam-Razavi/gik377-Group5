"""
Meddelandemallar för Notification Service.
Centraliserade texter för SMS och e-post.
"""


# --- Välkomstmeddelande (vid /subscribe) ---

def welcome_sms():
    return "Tack för att du registrerat dig för UNESCO-notiser! Du får meddelanden när du är nära ett världsarv."


def welcome_email_subject():
    return "Välkommen till UNESCO World Heritage-notiser"


def welcome_email_body(sites=None):
    text = "Hej!\n\nDin prenumeration är nu aktiv. Du kommer att få notifieringar när du befinner dig nära ett världsarv."
    if sites:
        text += "\n\nDu prenumererar på:\n"
        for site in sites:
            text += f"  - {site}\n"
    text += "\nMed vänliga hälsningar,\nUNESCO World Heritage Service"
    return text


# --- Platsbaserad notifikation (vid trigger) ---

def location_sms(site_name, link=None):
    msg = f"Du är nära {site_name}!"
    if link:
        msg += f" Läs mer: {link}"
    return msg


def location_email_subject(site_name):
    return f"UNESCO: Du är nära {site_name}"


def location_email_body(site_name, link=None):
    text = f"Hej!\n\nDu befinner dig nära världsarvet {site_name}."
    if link:
        text += f"\n\nLäs mer här: {link}"
    text += "\n\nMed vänliga hälsningar,\nUNESCO World Heritage Service"
    return text


# --- Bekräftelse vid avprenumeration ---

def unsubscribe_sms(sites=None):
    if sites:
        return "Du har avregistrerats från notiser för: %s." % ", ".join(sites)
    return "Du har avregistrerats från alla UNESCO-notiser."


def unsubscribe_email_subject():
    return "Bekräftelse: Avregistrering från UNESCO-notiser"


def unsubscribe_email_body(sites=None):
    if sites:
        text = "Hej!\n\nDu har avregistrerats från notiser för följande platser:\n"
        for site in sites:
            text += f"  - {site}\n"
    else:
        text = "Hej!\n\nDu har avregistrerats från alla UNESCO World Heritage-notiser.\n"
    text += "\nDu kan alltid registrera dig igen via vår tjänst."
    text += "\n\nMed vänliga hälsningar,\nUNESCO World Heritage Service"
    return text
