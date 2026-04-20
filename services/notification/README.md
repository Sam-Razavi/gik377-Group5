# Notification Service

Ansvarig: Riyaaq Ali

En fristående, leverantörsneutral modul för att skicka SMS och e-post.
Andra grupper kan:
- **anropa vår tjänst** via ett gemensamt HTTP-API (ingen kodändring krävs), eller
- **byta ut hela modulen** mot sin egen implementation så länge den följer API-kontraktet.

Vilken SMS- eller e-postleverantör som används internt är en implementationsdetalj
och syns aldrig i svaren – svarsfälten är alltid neutrala (`channel: "sms" | "email"`).


## Hur man kör igång

1. Se till att `.env`-filen finns i notification-mappen med API-nycklar (se "Nuvarande implementation" längst ned).
2. Lägg till detta i `app.py`:
```python
from services.notification import notification_bp
app.register_blueprint(notification_bp)
```
3. Starta servern med `python3 app.py`.
4. Testa att det funkar: gå till `http://127.0.0.1:5000/notification/health` – du ska se `{"status": "ok"}`.


## API-kontrakt (översikt)

| Endpoint | Metod | Vad den gör |
|---|---|---|
| `/notification/send-notification` | POST | Skicka ett SMS eller e-post direkt |
| `/notification/trigger-notification` | GET | Trigga platsnotis för en prenumerant |
| `/notification/subscribe` | POST | Registrera en användare |
| `/notification/unsubscribe` | POST | Avregistrera en användare |
| `/notification/subscribers` | GET | Lista alla prenumeranter (kräver admin-token) |
| `/notification/health` | GET | Kolla att tjänsten lever |

Alla svar följer samma mönster:
```json
{"success": true, "channel": "sms"}
{"success": false, "error": "cooldown", "message": "Notifiering redan skickad för denna plats och kanal nyligen."}
```

Fältet `channel` är alltid `"sms"` eller `"email"` - aldrig ett leverantörsnamn.
Det gör att modulen kan bytas ut utan att konsumenter behöver ändra kod.


## Endpoints

### Skicka SMS eller e-post

```
POST /notification/send-notification
```

Skicka med JSON i bodyn. Exempel SMS (minimalt):
```json
{
  "type": "sms",
  "to": "+46701234567",
  "message": "Du är nära Drottningholm!"
}
```

Exempel e-post (alla fält ifyllda):
```json
{
  "type": "email",
  "to": "user@example.com",
  "subject": "Du är nära Drottningholm",
  "message": "Du är nära Drottningholm - ett av UNESCO:s världsarv.",
  "user_id": "abc123",
  "site_id": "drottningholm_001"
}
```

- `type` - antingen `"sms"` eller `"email"` (obligatoriskt)
- `to` - telefonnummer med +46 eller e-postadress (obligatoriskt)
- `message` - texten som ska skickas (obligatoriskt)
- `subject` - ämnesrad, bara för e-post (valfritt)
- `user_id` - för att hålla koll på anti-spam (valfritt)
- `site_id` - för att hålla koll på anti-spam (valfritt)

Svar om det gick bra (HTTP 200):
```json
{"success": true, "channel": "sms"}
```

Svar om typen är ogiltig (HTTP 400):
```json
{"success": false, "error": "invalid_type", "message": "Ogiltig typ. Använd 'sms' eller 'email'."}
```

Svar om telefonnumret är ogiltigt (HTTP 400):
```json
{"success": false, "error": "invalid_recipient", "message": "Ogiltigt telefonnummer. Förväntat format: +46701234567"}
```

Svar om e-postadressen är ogiltig (HTTP 400):
```json
{"success": false, "error": "invalid_recipient", "message": "Ogiltig e-postadress."}
```

Svar om cooldown är aktiv (HTTP 429):
```json
{"success": false, "error": "cooldown", "message": "Notifiering redan skickad för denna plats och kanal nyligen."}
```

Svar om providern inte svarar (HTTP 500):
```json
{"success": false, "channel": "sms", "error": "Provider svarade inte efter flera försök."}
```

Statuskoder:
- 200 - Skickat
- 400 - Något fält saknas eller är ogiltigt
- 429 - Cooldown, redan skickat nyligen
- 500 - Providern svarade inte

Felkoder (fältet `error`):
- `invalid_type` - `type` är varken `"sms"` eller `"email"`
- `invalid_recipient` - `to` har fel format
- `cooldown` - redan notifierad inom cooldown-perioden


### Trigga notifiering baserat på position

```
GET /notification/trigger-notification?user_id=abc123&site_id=drottningholm_001&site_name=Drottningholm
```

- `user_id` - vem som ska få notifieringen (obligatoriskt)
- `site_id` - vilket världsarv (obligatoriskt)
- `site_name` - namn på världsarvet (valfritt)
- `link` - länk till mer info (valfritt)

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
2. **Platsbaserad** – skickas när någon är nära ett världsarv.
3. **Avregistrering** – skickas när någon avprenumererar.

Alla tre skickas både som SMS och e-post om användaren har registrerat båda.


## Anti-spam

Max 1 notifiering per användare, per världsarv, per kanal (SMS/e-post) inom 1 timme.
Det går att ändra tidsgränsen via `NOTIFICATION_COOLDOWN` i `.env` (i sekunder).


## Lagring

Prenumeranter och skickade notifieringar sparas i en PostgreSQL-databas.
Tabellerna (`subscribers`, `subscriber_sites`, `sent_log`) skapas automatiskt vid uppstart.
Data finns kvar även om servern startas om.

Anslutningen konfigureras via miljövariabler i `.env`:

```
NOTIFICATION_PG_HOST=localhost
NOTIFICATION_PG_PORT=5432
NOTIFICATION_PG_DATABASE=notification
NOTIFICATION_PG_USER=postgres
NOTIFICATION_PG_PASSWORD=changeme
```

Skapa databasen innan första start:

```bash
createdb notification
```


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


## Nuvarande implementation (intern detalj)

Dessa val är **inte** en del av det publika kontraktet och kan bytas utan att
andra grupper märker det:

- **SMS-leverantör:** HelloSMS (klass `SMSProvider` i `providers.py`)
- **E-postleverantör:** SMTP2GO (klass `EmailProvider` i `providers.py`)
- **Databas:** PostgreSQL via `psycopg2`

För att byta leverantör räcker det att skriva om `SMSProvider.send()` eller
`EmailProvider.send()` – inga ändringar behövs i `service.py`, `routes.py`
eller hos konsumenter av API:et.
