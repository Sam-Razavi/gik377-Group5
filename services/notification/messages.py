"""
Meddelandemallar för Notification Service.
Centraliserade texter för SMS och e-post.
"""


def _gdpr_notice():
    """GDPR-informationstext som läggs in i välkomstmejl."""
    return (
        "\n\n---\n"
        "Om din personuppgiftsbehandling:\n"
        "Vi lagrar ditt telefonnummer och/eller din e-postadress tillsammans "
        "med vilka världsarv du valt att prenumerera på. Uppgifterna används "
        "enbart för att skicka dig notifieringar och lämnas aldrig ut till "
        "tredje part. Du kan när som helst avregistrera dig - då raderas all "
        "din data från våra system.\n"
    )


# --- Välkomstmeddelande (vid /subscribe) ---

def welcome_sms():
    return (
        "Tack för att du registrerat dig! Vi hör av oss när du är nära "
        "ett UNESCO-världsarv, så du inte missar en plats värd att "
        "upptäcka. Svara STOP för att avsluta."
    )


def welcome_email_subject():
    return "Välkommen - din resa genom världsarven börjar nu"


def welcome_email_body(sites=None):
    text = (
        "Hej och välkommen!\n\n"
        "Din prenumeration är aktiv. Från och med nu får du en knuff "
        "varje gång du befinner dig nära ett av UNESCO:s världsarv - "
        "platser som valts ut för sitt enastående värde för mänskligheten.\n\n"
        "Vad du kan förvänta dig:\n"
        "  • En kort notis när du är i närheten av ett världsarv\n"
        "  • Länk för att läsa mer om platsen\n"
        "  • Inget spam - bara relevanta meddelanden i rätt ögonblick"
    )
    if sites:
        text += "\n\nDu prenumererar på:\n"
        for site in sites:
            text += f"  • {site}\n"
    text += "\nTrevlig upptäcktsresa!\nUNESCO World Heritage Service"
    text += _gdpr_notice()
    return text


# --- Platsbaserad notifikation (vid trigger) ---

def location_sms(site_name, link=None):
    msg = f"Du är nära {site_name} - ett av UNESCO:s världsarv. Ta chansen att upptäcka det."
    if link:
        msg += f" Läs mer: {link}"
    msg += " Svara STOP för att avsluta."
    return msg


def location_email_subject(site_name):
    return f"Du är nära {site_name} - ett världsarv att upptäcka"


def location_email_body(site_name, link=None):
    text = (
        f"Hej!\n\n"
        f"Du är precis i närheten av {site_name} - ett av UNESCO:s "
        f"världsarv. En plats med historia som är värd ett besök."
    )
    if link:
        text += f"\n\nLäs mer här: {link}"
    text += "\n\nTrevlig upptäcktsresa!\nUNESCO World Heritage Service"
    return text


# --- Bekräftelse vid avprenumeration ---

def unsubscribe_sms(sites=None):
    if sites:
        return (
            "Du har avregistrerats från notiser för: %s. "
            "Tack för den här tiden - välkommen tillbaka när du vill!"
            % ", ".join(sites)
        )
    return (
        "Du har avregistrerats från UNESCO-notiser. "
        "Tack för den här tiden - välkommen tillbaka när du vill!"
    )


def unsubscribe_email_subject():
    return "Bekräftelse: du är nu avregistrerad"


def unsubscribe_email_body(sites=None):
    if sites:
        text = "Hej!\n\nDu har avregistrerats från notiser för följande platser:\n"
        for site in sites:
            text += f"  • {site}\n"
    else:
        text = (
            "Hej!\n\n"
            "Du är nu avregistrerad från alla UNESCO World Heritage-notiser.\n"
        )
    text += (
        "\nTack för att du använt tjänsten. Vill du komma tillbaka senare "
        "är du alltid välkommen att registrera dig igen via appen."
    )
    text += "\n\nVi ses,\nUNESCO World Heritage Service"
    return text
