# Notification Service

Ansvarig: Riyaaq Ali

En fristående modul för att skicka SMS och e-post. Andra grupper kan använda den genom att anropa våra endpoints.


## Hur man kör igång

1. Se till att `.env`-filen finns i notification-mappen med API-nycklar (HelloSMS och SMTP2GO).
2. Lägg till detta i `app.py`:
```python
from services.notification import notification_bp
app.register_blueprint(notification_bp)
```
3. Starta servern med `python3 app.py`.
4. Testa att det funkar: gå till `http://127.0.0.1:5000/notification/health` – du ska se `{"status": "ok"}`.


## Endpoints

### Skicka SMS eller e-post

```
POST /notification/send-notification
```

Skicka med JSON i bodyn:
```json
{
  "type": "sms",
  "to": "+46701234567",
  "message": "Du är nära Drottningholm!"
}
```

- `type` – antingen `"sms"` eller `"email"` (obligatoriskt)
- `to` – telefonnummer med +46 eller e-postadress (obligatoriskt)
- `message` – texten som ska skickas (obligatoriskt)
- `subject` – ämnesrad, bara för e-post (valfritt)
- `user_id` – för att hålla koll på anti-spam (valfritt)
- `site_id` – för att hålla koll på anti-spam (valfritt)

Svar om det gick bra:
```json
{"success": true, "provider": "hellosms"}
```

Svar om det gick fel:
```json
{"success": false, "error": "cooldown", "message": "Notifiering redan skickad..."}
```

Statuskoder:
- 200 – Skickat
- 400 – Något fält saknas eller är ogiltigt
- 429 – Cooldown, redan skickat nyligen
- 500 – Providern (HelloSMS/SMTP2GO) svarade inte


### Trigga notifiering baserat på position

```
GET /notification/trigger-notification?user_id=abc123&site_id=drottningholm_001&site_name=Drottningholm
```

- `user_id` – vem som ska få notifieringen (obligatoriskt)
- `site_id` – vilket världsarv (obligatoriskt)
- `site_name` – namn på världsarvet (valfritt)
- `link` – länk till mer info (valfritt)

Användaren måste vara prenumerant och ha den platsen i sin lista. Annars får man 404.


### Prenumerera

```
POST /notification/subscribe
```

```json
{
  "user_id": "abc123",
  "phone": "+46701234567",
  "email": "user@example.com",
  "sites": ["drottningholm_001", "visby_002"]
}
```

Användaren får automatiskt ett välkomst-SMS och/eller välkomstmejl.


### Avprenumerera

```
POST /notification/unsubscribe
```

```json
{
  "user_id": "abc123",
  "sites": ["drottningholm_001"]
}
```

Lämna bort `sites` för att ta bort allt. Användaren får ett bekräftelsemeddelande.


### Healthcheck

```
GET /notification/health
```

Returnerar `{"status": "ok"}` om tjänsten lever.


## Meddelandetyper

Det finns tre typer av meddelanden som skickas automatiskt:

1. **Välkomst** – skickas när någon prenumererar.
   SMS: "Tack för att du registrerat dig för UNESCO-notiser!"

2. **Platsbaserad** – skickas när någon är nära ett världsarv.
   SMS: "Du är nära Drottningholm! Läs mer: ..."

3. **Avregistrering** – skickas när någon avprenumererar.
   SMS: "Du har avregistrerats från notiser för: Drottningholm."

Alla tre skickas både som SMS och e-post om användaren har registrerat båda.


## Anti-spam

Max 1 notifiering per användare, per världsarv, per kanal (SMS/e-post) inom 1 timme.
Det går att ändra tidsgränsen via `NOTIFICATION_COOLDOWN` i `.env` (i sekunder).


## Lagring

Prenumeranter och skickade notifieringar sparas i en SQLite-databas (`notification.db`).
Filen skapas automatiskt. Data finns kvar även om servern startas om.


## Hur en annan grupp använder tjänsten

Ändra bara URL:en till vår server:

```python
import requests

requests.post("https://vår-server.com/notification/send-notification", json={
    "type": "sms",
    "to": "+46701234567",
    "message": "Hej!"
})
```

Ingen annan kodändring behövs. Vill man byta tillbaka ändrar man bara URL:en igen.
