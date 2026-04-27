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
2. Routern registreras automatiskt i `app.py`:
```python
from services.notification.routes import router as notification_router
app.include_router(notification_router)
```
3. Starta servern med `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`.
4. Testa att det funkar: gå till `http://127.0.0.1:8000/api/notification/health` – du ska se `{"status": "ok", "service": "notification"}`.


## API-kontrakt (översikt)

Alla endpoints ligger under prefix `/api/notification`.

| Endpoint | Metod | Vad den gör |
|---|---|---|
| `/api/notification/send` | POST | Skicka ett SMS eller e-post direkt |
| `/api/notification/trigger` | GET | Trigga platsnotis för en prenumerant |
| `/api/notification/subscribe` | POST | Registrera en användare |
| `/api/notification/unsubscribe` | POST | Avregistrera en användare |
| `/api/notification/mark-visited` | POST | Markera världsarv som besökt (stoppar framtida notiser) |
| `/api/notification/subscribers` | GET | Lista alla prenumeranter (kräver admin-token) |
| `/api/notification/health` | GET | Kolla att tjänsten lever |

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
POST /api/notification/send
```

Skicka med JSON i bodyn. Exempel SMS (minimalt):
```json
{
  "channel": "sms",
  "to": "+46701234567",
  "message": "Du är nära Drottningholm!"
}
```

Exempel e-post (alla fält ifyllda):
```json
{
  "channel": "email",
  "to": "user@example.com",
  "subject": "Du är nära Drottningholm",
  "message": "Du är nära Drottningholm - ett av UNESCO:s världsarv.",
  "user_id": "abc123",
  "site_id": "drottningholm_001"
}
```

- `channel` - antingen `"sms"` eller `"email"` (obligatoriskt)
- `to` - telefonnummer med +46 eller e-postadress (obligatoriskt)
- `message` - texten som ska skickas (obligatoriskt)
- `subject` - ämnesrad, bara för e-post (valfritt)
- `user_id` - för att hålla koll på anti-spam (valfritt)
- `site_id` - för att hålla koll på anti-spam (valfritt)

Svar om det gick bra (HTTP 200):
```json
{"success": true, "channel": "sms"}
```

Svar om kanalen är ogiltig (HTTP 400):
```json
{"success": false, "error": "invalid_channel", "message": "Ogiltig kanal. Använd 'sms' eller 'email'."}
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
- `invalid_channel` - `channel` är varken `"sms"` eller `"email"`
- `invalid_recipient` - `to` har fel format
- `cooldown` - redan notifierad inom cooldown-perioden


### Trigga notifiering baserat på position

```
GET /api/notification/trigger?user_id=abc123&site_id=drottningholm_001&site_name=Drottningholm
```

- `user_id` - vem som ska få notifieringen (obligatoriskt)
- `site_id` - vilket världsarv (obligatoriskt)
- `site_name` - namn på världsarvet (valfritt, default `"Okänt världsarv"`)
- `link` - länk till mer info (valfritt; om utelämnad bygger backend själv `{SITE_PAGE_BASE_URL}?id={site_id}`)

Skickar SMS och/eller e-post beroende på prenumerantens registrerade kontaktuppgifter.
Om användaren redan har markerat världsarvet som besökt skickas ingenting.

Användaren måste vara prenumerant och ha den platsen i sin lista. Annars får man 404.


### Prenumerera

```
POST /api/notification/subscribe
```

```json
{
  "user_id": "abc123",
  "phone": "+46701234567",
  "email": "user@example.com",
  "sites": ["drottningholm_001", "visby_002"]
}
```

Användaren får automatiskt ett välkomst-SMS och/eller välkomstmejl vid första registreringen.


### Avprenumerera

```
POST /api/notification/unsubscribe
```

```json
{
  "user_id": "abc123",
  "sites": ["drottningholm_001"]
}
```

Lämna bort `sites` för att ta bort allt. Användaren får ett bekräftelsemeddelande.


### Markera världsarv som besökt

```
POST /api/notification/mark-visited
```

```json
{
  "user_id": "abc123",
  "site_id": "drottningholm_001"
}
```

Markerar världsarvet som besökt för användaren. Inga fler notiser skickas
för denna kombination av `user_id` + `site_id`, även om cooldown gått ut.

Svar:
```json
{"success": true, "user_id": "abc123", "site_id": "drottningholm_001", "visited": true}
```


### Healthcheck

```
GET /api/notification/health
```

Returnerar `{"status": "ok", "service": "notification"}` om tjänsten lever.


### Lista prenumeranter (intern)

```
GET /api/notification/subscribers
Header: Authorization: Bearer <NOTIFICATION_ADMIN_TOKEN>
```

Returnerar 403 utan giltig token.


## Meddelandetyper

Det finns tre typer av meddelanden som skickas automatiskt:

1. **Välkomst** – skickas när någon prenumererar för första gången.
2. **Platsbaserad** – skickas när någon är nära ett världsarv (via `/trigger`).
3. **Avregistrering** – skickas när någon avprenumererar.

Alla tre skickas både som SMS och e-post om användaren har registrerat båda.


## Anti-spam (cooldown)

Max 1 notifiering per användare, per världsarv, per kanal (SMS/e-post) inom cooldown-fönstret.
Cooldown är **olika per kanal** eftersom SMS kostar mer än e-post:

- **SMS:** 720 timmar (30 dagar) – konfigureras via `NOTIFICATION_COOLDOWN_SMS_HOURS`
- **E-post:** 168 timmar (7 dagar) – konfigureras via `NOTIFICATION_COOLDOWN_EMAIL_HOURS`

Värdena anges i timmar i `.env`. Räknas om till sekunder internt.

**Permanent block:** Användare som markerat ett världsarv som besökt via `/mark-visited`
får aldrig fler notiser för det världsarvet, oavsett cooldown.


## Lagring

Prenumeranter och skickade notifieringar sparas i en PostgreSQL-databas.
Tabellerna (`subscribers`, `subscriber_sites`, `sent_log`) skapas automatiskt vid uppstart.
`subscriber_sites` har en `visited`-kolumn som styr permanent block.
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

requests.post("https://vår-server.com/api/notification/send", json={
    "channel": "sms",
    "to": "+46701234567",
    "message": "Hej!"
})
```

Ingen annan kodändring behövs. Vill man byta tillbaka ändrar man bara URL:en igen.


## Konfiguration (.env)

```
# Provider – HelloSMS
HELLOSMS_API_URL=https://api.hellosms.se/v1/
HELLOSMS_USERNAME=...
HELLOSMS_PASSWORD=...

# Provider – SMTP2GO
SMTP2GO_API_URL=https://api.smtp2go.com/v3/
SMTP2GO_API_KEY=api-...
SMTP2GO_SENDER=nordicdigitalsolutions@hotmail.com

# Admin & DB
NOTIFICATION_ADMIN_TOKEN=admintoken123
NOTIFICATION_PG_HOST=localhost
NOTIFICATION_PG_PORT=5432
NOTIFICATION_PG_DATABASE=notification
NOTIFICATION_PG_USER=postgres
NOTIFICATION_PG_PASSWORD=postgres

# Cooldown (timmar)
NOTIFICATION_COOLDOWN_SMS_HOURS=720
NOTIFICATION_COOLDOWN_EMAIL_HOURS=168

# Bas-URL till världsarvssidan (länken som skickas i SMS/mejl)
SITE_PAGE_BASE_URL=https://nordicdigitalsolutions.se/site.html
```


## Nuvarande implementation (intern detalj)

Dessa val är **inte** en del av det publika kontraktet och kan bytas utan att
andra grupper märker det:

- **Webbramverk:** FastAPI (router i `routes.py`)
- **SMS-leverantör:** HelloSMS (klass `SMSProvider` i `providers.py`)
- **E-postleverantör:** SMTP2GO (klass `EmailProvider` i `providers.py`)
- **Databas:** PostgreSQL via `psycopg2`

För att byta leverantör räcker det att skriva om `SMSProvider.send()` eller
`EmailProvider.send()` – inga ändringar behövs i `service.py`, `routes.py`
eller hos konsumenter av API:et.
