# DjangoWeatherReminder

A REST API service that sends **weather notifications** for subscribed cities via **email** and **webhook**, on a schedule chosen per subscription (every 1, 3, 6, or 12 hours).

Users manage subscriptions through a web interface or entirely over the API — third-party services register, receive a **JWT**, and drive everything programmatically. Weather comes from a third-party provider and is cached per city, so many subscribers to the same city cost a single API call.

**Live app:** https://weather-reminder-web-182409292391.europe-west3.run.app
**API docs:** https://weather-reminder-web-182409292391.europe-west3.run.app/api/docs/

**Demo account:** `demo@example.com` / `DemoPass2026` — comes with two subscriptions already set up, so the dashboard isn't empty.

---

## What it does

- **Web interface** — sign up, log in, and manage subscriptions in a browser.
- **REST API** — the same operations over HTTP with JWT auth, for programmatic clients.
- **Subscribe** to one or many cities, each with a notification **period** (1, 3, 6 or 12 hours) and a **delivery channel** (email or webhook).
- **Edit**, **delete**, or **list** your own subscriptions.
- Deliver notifications **automatically on schedule**, in the background.
- Pull live weather from **OpenWeatherMap**, cached in the database.

---

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Django + Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) for the API, sessions for the web UI |
| Database | PostgreSQL (Neon in production) |
| Background tasks | Celery |
| Broker | Redis (Upstash in production) |
| Scheduling | Celery Beat locally, Cloud Scheduler in production |
| Weather data | OpenWeatherMap — swappable behind a provider interface |
| Email | SMTP (Brevo in production, console backend locally) |
| API docs | OpenAPI 3 via `drf-spectacular` — Swagger UI and ReDoc |
| Static files | WhiteNoise |
| Tests | pytest + pytest-cov — 65 tests, 93% coverage |
| Lint/format | ruff, enforced in CI |
| Containers | Docker + Docker Compose |
| Deployment | Google Cloud Run (web service + worker pool) |

---

## Architecture

The service is two processes that never call each other directly — they communicate through the database and a task queue.

```
                        ┌─────────────────────────────┐
   Browser ── session ─►│                             │
                        │      Django + DRF (web)     │
   API client ── JWT ──►│   accounts / weather /      │
                        │   subscriptions / web       │
                        └──────────┬──────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────────────┐
                        │         PostgreSQL          │
                        │  User, City, Subscription,  │
                        │  WeatherSnapshot            │
                        └──────────▲──────────────────┘
                                   │
   Celery Beat (local)             │
   Cloud Scheduler (production)    │
          │                        │
          │  hourly                │
          ▼                        │
   ┌──────────────┐         ┌──────┴────────┐
   │    Redis     │────────►│ Celery worker │
   │   (queue)    │         └──────┬────────┘
   └──────────────┘                │
                                   ├──► OpenWeatherMap (via cache)
                                   ├──► Email (SMTP)
                                   └──► Webhook (POST)
```

**Why two processes.** Django works on request → response; it has no way to do something every hour on its own. The web service handles HTTP and returns immediately. The worker does the slow work — fetching weather, sending mail — so a dead webhook URL or a slow provider never affects API latency.

**Scheduling state lives on each row**, not in the scheduler. `Subscription.last_notified_at` plus `is_due()` decide who gets notified, so workers are stateless: run several, restart them, redeploy mid-cycle, and the schedule stays correct.

### Layers

```
HTTP request
   │
   ▼  URL router → permission → view (HTTP only)
   ▼  serializer / form (validation)
   ▼  service layer (business logic)
   ▼  provider / notifier (external world, behind interfaces)
   ▼  model / ORM
```

Views do HTTP and nothing else. `notify_one` (a Celery task) and `CurrentWeatherView` (an HTTP view) call the same `get_weather(city)` — the caching logic is written once.

### Two Strategy-pattern implementations

```
WeatherProvider (interface)          Notifier (interface)
   get_current(city) → WeatherData      send(subscription, snapshot)
        │                                    │
        └── OpenWeatherProvider              ├── EmailNotifier
                                             └── WebhookNotifier
                                                    ▲
                                        NotificationDispatcher
                                        (selects by delivery_method)
```

Swapping weather providers is one new class. Adding SMS delivery is one new class plus one dictionary entry. Tests mock the interface rather than the network.

---

## Project structure

| App | Responsibility |
|---|---|
| `accounts` | Custom email-based user, registration, JWT wiring |
| `weather` | `City` and `WeatherSnapshot`, provider interface, caching service, weather endpoints |
| `subscriptions` | `Subscription` + CRUD API, notifiers, dispatcher, Celery tasks |
| `web` | Server-rendered UI — signup, login, dashboard, subscription forms |

```
django-weather-reminder/
├── weather_reminder/        # settings, urls, celery.py
├── accounts/
│   ├── models.py            # custom User (email login) + UserManager
│   ├── serializers.py       # RegisterSerializer
│   └── views.py             # registration endpoint
├── weather/
│   ├── models.py            # City, WeatherSnapshot (+ is_fresh)
│   ├── providers.py         # WeatherProvider interface + OpenWeatherProvider
│   ├── services.py          # get_weather(): cache → fetch → store
│   ├── views.py             # city search + current weather
│   └── fixtures/cities.json # 25 European cities
├── subscriptions/
│   ├── models.py            # Subscription (+ is_due)
│   ├── serializers.py       # cross-field validation
│   ├── permissions.py       # IsOwner
│   ├── views.py             # SubscriptionViewSet + scheduler endpoint
│   ├── notifiers.py         # Notifier interface, Email/Webhook notifiers
│   ├── dispatcher.py        # selects a notifier by delivery_method
│   └── tasks.py             # process_subscriptions, notify_one
├── web/
│   ├── forms.py             # signup + subscription forms
│   ├── views.py             # session-authenticated HTML views
│   └── templates/web/
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Data model

- **`User`** — custom user; email is the login identifier, no username.
- **`City`** — name, country code, latitude, longitude. Weather is fetched by coordinates, not name, so ambiguous city names aren't a problem.
- **`Subscription`** — links a user to a city; holds `period_hours`, `delivery_method`, `webhook_url`, `is_active`, `last_notified_at`. `is_due()` decides when the next notification fires.
- **`WeatherSnapshot`** — cached weather per city with `is_fresh()`. 500 subscribers to Warsaw cost one API call, not 500.

---

## API reference

Base path: `/api/`. Interactive docs at `/api/docs/`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register/` | – | Create an account |
| POST | `/auth/token/` | – | Obtain access + refresh JWT |
| POST | `/auth/token/refresh/` | – | Refresh the access token |
| GET | `/cities/?search=<q>` | JWT | Search / list cities |
| GET | `/weather/?city_id=<id>` | JWT | Current weather for a city |
| GET | `/subscriptions/` | JWT | List your subscriptions |
| POST | `/subscriptions/` | JWT | Create a subscription |
| GET | `/subscriptions/{id}/` | JWT | Retrieve one |
| PATCH | `/subscriptions/{id}/` | JWT | Edit period / channel / pause |
| DELETE | `/subscriptions/{id}/` | JWT | Unsubscribe |
| POST | `/tasks/run-notifications/` | shared secret | Queue a notification run (scheduler only) |
| GET | `/schema/` · `/docs/` · `/redoc/` | – | OpenAPI schema, Swagger UI, ReDoc |

### Status codes

| Code | When | Why that one |
|---|---|---|
| 201 | subscription created | resource created |
| 202 | scheduler endpoint | accepted — the work is queued, not finished |
| 204 | unsubscribe | success, nothing to return |
| 400 | missing `city_id`, webhook without URL | malformed request |
| 401 | missing or expired token | not authenticated |
| 403 | wrong scheduler token | authenticated but not allowed |
| 404 | another user's subscription | doesn't reveal that the resource exists |
| 502 | weather provider unreachable | the upstream failed, not this service |

### Example: authenticate and subscribe

```bash
BASE=https://weather-reminder-web-182409292391.europe-west3.run.app

# 1. Get a token
curl -X POST $BASE/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
# -> { "access": "<jwt>", "refresh": "<jwt>" }

# 2. Find a city
curl "$BASE/api/cities/?search=warsaw" -H "Authorization: Bearer <jwt>"

# 3. Subscribe (email, every 3 hours)
curl -X POST $BASE/api/subscriptions/ \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"city": 1, "period_hours": 3, "delivery_method": "email"}'
```

For webhook delivery, pass `"delivery_method": "webhook"` and a `"webhook_url"`.

---

## Security model

- **Two-layer ownership isolation.** `get_queryset()` filters by `request.user` so other users' subscriptions never appear in a list, and because detail routes look up objects within that queryset, requesting someone else's ID returns **404** rather than 403 — the API doesn't reveal that the resource exists. `IsOwner` is a second, object-level check.
- **The owner is set server-side.** `user` isn't a writable serializer field; `perform_create` takes it from the request, so a client can't create a subscription in someone else's name.
- **`IsAuthenticated` is the global default**, so endpoints are closed unless explicitly opened — fail-closed rather than fail-open.
- **`last_notified_at` is read-only** over the API. It's scheduling state owned by the worker; a client able to edit it could force repeated sends.
- **Passwords are hashed** via a custom manager's `create_user`, with Django's validators wired into both the serializer and the signup form.
- **Secrets come from the environment** — never committed. `.env.example` documents every key with empty values.

---

## How notifications work

1. **Celery Beat** (local) or **Cloud Scheduler** (production) triggers hourly.
2. `process_subscriptions` loads active subscriptions and checks `is_due()` on each.
3. For every due subscription it queues a separate `notify_one` task — so one dead webhook URL can't sink the whole batch.
4. `notify_one` gets weather from the **cache** or fetches it once and stores it.
5. The dispatcher selects a notifier by `delivery_method` and sends.
6. `last_notified_at` is updated **only after a successful send**, so a failure retries on the next cycle instead of being silently marked as delivered.

---

## Running locally

### With Docker (recommended)

Runs all five services — web, Celery worker, Celery beat, Postgres, Redis — with one command.

```bash
git clone https://github.com/YuriiLev/django-weather-reminder.git
cd django-weather-reminder
cp .env.example .env      # fill in the values
docker compose up --build

# in a second terminal:
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata cities
docker compose exec web python manage.py createsuperuser
```

The app is available at `http://localhost:8000/`.

### Without Docker

Requires local PostgreSQL and Redis.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata cities
python manage.py createsuperuser

# four processes, each in its own terminal:
python manage.py runserver
celery -A weather_reminder worker -l info --pool=solo   # --pool=solo is Windows-only
celery -A weather_reminder beat -l info
# (Redis must be running)
```

### Environment variables

See `.env.example` for the full list.

```dotenv
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=

DATABASE_URL=postgres://user:password@127.0.0.1:5432/weather_reminder
CELERY_BROKER_URL=redis://127.0.0.1:6379/0

WEATHER_API_KEY=
WEATHER_CACHE_MINUTES=30

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

SCHEDULER_TOKEN=
```

The console email backend prints messages to the terminal, so local development needs no mail account.

---

## Tests

```bash
pytest
```

**65 tests, 93% coverage.** External calls are mocked, so the suite runs offline and deterministically.

Covered:

- **Auth** — registration, token issue and refresh, password hashing, weak-password rejection
- **Ownership isolation** — user B can't see, retrieve, edit or delete user A's subscriptions, in both the API and the web UI
- **Validation** — webhook requires a URL, including on partial updates
- **Scheduling** — `is_due()` across never-notified, recently-notified, elapsed and inactive states
- **Caching** — a fresh snapshot is served without any HTTP call (asserted via `assert_not_called`)
- **Notifications** — email and webhook notifiers, dispatcher selection, and that a failed send does **not** record `last_notified_at`
- **Celery tasks** — called directly as functions, so no broker or worker is needed
- **Web UI** — login-required redirects, owner-set-from-request, and that a GET can't delete

---

## CI

GitHub Actions runs `ruff format --check` and `ruff check` on every push and pull request.

---

## Deployment

Deployed to **Google Cloud Run** in `europe-west3`, built from the same Dockerfile used locally.

| Component | Service |
|---|---|
| Web API + UI | Cloud Run service (public) |
| Celery worker | Cloud Run **worker pool**, always on |
| Database | Neon (pooled connection) |
| Broker | Upstash Redis over TLS |
| Email | Brevo SMTP |
| Schedule | Cloud Scheduler, hourly |

### Background work in production

App Engine can't keep an always-on process alive, which is why the earlier version of this project had to run tasks **synchronously inside the HTTP request**. Cloud Run solves it properly: the worker is a **worker pool** — a service type with no HTTP surface and no health check — running the same image with a different command.

The flow:

1. **Cloud Scheduler** sends an hourly `POST` to `/api/tasks/run-notifications/`, guarded by a shared secret in the `X-Scheduler-Token` header.
2. The endpoint **only queues** the task and returns **202 Accepted** immediately — no work happens on the request path.
3. The **Celery worker** picks it up from Upstash Redis and does the fetching and sending.

Locally the same tasks run under Celery Beat with Redis in Compose. Only the trigger differs; the task code is identical.

```bash
gcloud scheduler jobs create http notify-subscribers \
  --location=europe-west3 \
  --schedule="0 * * * *" \
  --uri="https://<app-url>/api/tasks/run-notifications/" \
  --http-method=POST \
  --headers="X-Scheduler-Token=<production-token>,Content-Type=application/json" \
  --message-body="{}"
```

---

## Notes on the rebuild

This is a rebuild of an earlier version of the project, written from scratch to fix its production architecture. The original deployed to App Engine, where Celery couldn't run — tasks executed inline in the request. This version runs a real Celery worker in production.

Other changes: the service layer and configurable settings were designed in from the start rather than extracted after review, `DATABASE_URL` replaced five separate connection variables, OpenAPI documentation and a web UI were added, and CI ran from the first commit.