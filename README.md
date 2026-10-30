# InternLink — Internship Placement Portal

A standalone Django application that connects students looking for internships with employers, with an internship coordinator overseeing the whole process. It covers the full placement pipeline: company and posting approval, applications, shortlisting, interviews, offers, and acceptance.

This project is independent of the existing `hrmo_tracker` project and has its own database, settings, and virtual environment.

## Features

### Students
- Browse, search, and filter published internship postings by keyword, work mode, and deadline.
- View company profiles and verified badges.
- Bookmark postings for later.
- Apply with a resume upload and cover letter (one application per posting).
- Track application status with a full history timeline.
- Withdraw active applications.
- Respond to internship offers (accept or decline).
- Manage a profile with school, course, skills, bio, resume, LinkedIn, and portfolio links.
- Receive in-app notifications for status changes.

### Employers
- Create and maintain a company profile.
- Create internship postings as drafts and submit them for coordinator review.
- Manage postings and view applicant counts.
- Review applications scoped to their own company only.
- Move applicants through the pipeline: under review → shortlisted → interview → offered → accepted/rejected.
- Add internal notes visible only to employers and coordinators.
- Schedule on-site, online, or phone interviews.
- Extend offers with start/end dates, stipend, details, and a response deadline.
- View an employer dashboard with pipeline metrics and upcoming interviews.
- Access reports for their own postings.

### Internship Coordinator
- Review the posting queue and approve, reject, or publish submissions.
- Verify companies.
- Access all postings, applications, companies, and reports.
- Oversee pipeline activity across every employer.
- Use the Django admin for full data administration.

### Platform
- Custom email-based user model with three roles: `student`, `employer`, `coordinator`.
- Role-aware dashboards and permissions.
- Application status transitions enforced by a central service layer.
- Notification system with unread-count context processor.
- Responsive Bootstrap 5 interface with crispy forms.
- Demo data seed command for quick evaluation.
- Automated test suite covering models, permissions, and pipeline behavior.

## Application pipeline

```
submitted ──► under_review ──► shortlisted ──► interview ──► offered ──► accepted
    │              │               │              │            │
    └──────────────┴───────────────┴──────────────┴────────────┴──► rejected
    └──────────────┴───────────────┴──────────────┴────────────┴──► withdrawn
```

Allowed transitions are defined in `Application.TRANSITIONS` and enforced through `applications/services.py`. Postings follow:

```
draft ──► pending ──► published ──► closed
              │
              └──► rejected / returned to draft
```

## Tech stack

- Python 3.10+ (developed with Django 5.2)
- Django 5.2.18
- SQLite (development default)
- Bootstrap 5 via `crispy-bootstrap5`
- `django-crispy-forms`
- `python-dotenv`
- Django templates and class-based views

## Getting started

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
cd internship_portal
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
cd internship_portal
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables (optional)

Copy `.env.example` to `.env` and adjust values as needed:

```env
DJANGO_SECRET_KEY=replace-this-with-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DEFAULT_FROM_EMAIL=internlink@example.com
```

The project runs with safe development defaults if no `.env` file is present.

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Load demo data (recommended)

```bash
python manage.py seed_demo
```

This creates demo companies, postings, students, applications, interviews, offers, bookmarks, and notifications.

### 6. Run the development server

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

## Demo accounts

All demo accounts use the password `demo12345`.

| Role | Email |
| --- | --- |
| Coordinator | `coordinator@internlink.test` |
| Employer — Northwind Analytics | `employer@northwind.test` |
| Employer — BrightWave Studio | `employer@brightwave.test` |
| Student — Alex Cruz | `student@university.test` |
| Student — Maria Santos | `student2@university.test` |

The Django admin is available at <http://127.0.0.1:8000/admin/>. Create a superuser with:

```bash
python manage.py createsuperuser
```

## Running tests

```bash
python manage.py test
```

The suite currently contains 32 tests covering accounts, postings, permissions, applications, interviews, offers, notifications, and dashboards.

Useful checks:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Project structure

```
internship_portal/
├── accounts/          # Custom user, student/employer profiles, auth views
├── applications/      # Applications, status history, notes, interviews, offers
├── config/            # Settings, root URLs, WSGI/ASGI
├── dashboard/         # Role-aware dashboards and reports
├── notifications/     # In-app notifications
├── opportunities/     # Companies, internship postings, bookmarks
├── static/            # Project CSS, JS, PWA manifest, app icons
├── templates/         # Shared and app templates (incl. pwa/)
├── tools/             # Developer scripts (icon generator)
├── manage.py
├── requirements.txt
├── build.sh            # Render build script
├── Procfile            # Gunicorn start command
├── render.yaml         # Render Blueprint (web service + Postgres)
├── .python-version     # Python version for hosting
├── .env.example
└── README.md
```

## Permissions model

- **Students** can only see their own applications and profile.
- **Employers** can only manage their own company, postings, and applications for those postings.
- **Coordinators** have read/write oversight of all companies, postings, applications, and reports.
- Object-level checks are implemented in views and query scoping, not only in templates.

## File uploads

- Resumes are stored under `media/resumes/`.
- Application resumes use randomized filenames to avoid collisions.
- Development serves media through Django when `DEBUG=True`.
- In production, configure a web server or object storage for `MEDIA_ROOT`.

## Deploy to Render

Render is the primary target for this project. The repository includes a `render.yaml` Blueprint, `build.sh`, and `Procfile`, so Render deploys it directly from GitHub with a PostgreSQL database attached.

### 1. Push the project to GitHub

The repository is already at `https://github.com/kanuisaiahkelvin-a11y/internship_portal`.

### 2. Create the Blueprint

1. Sign in at <https://dashboard.render.com/>.
2. Click **New → Blueprint**.
3. Connect the `internship_portal` repository and click **Connect**.
4. Render reads `render.yaml` and shows a service (`internlink`) and a database (`internlink-db`).
5. When prompted for `DJANGO_SUPERUSER_PASSWORD`, enter a strong admin password.
6. Click **Apply**.

### 3. Wait for the build

Render runs `bash build.sh`, which:

```bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py bootstrap
```

Then the `initialDeployHook` runs once after the first successful deploy:

```bash
python manage.py bootstrap --seed
```

The site goes live at the `.onrender.com` URL shown in the dashboard.

### 4. Log in

```
https://YOUR-SERVICE.onrender.com/admin/
```

| Field | Value |
| --- | --- |
| Email | `admin@internlink.test` |
| Password | the one you entered during Blueprint creation |

Demo accounts use the password `demo12345`. To skip the demo dataset, delete the `initialDeployHook` line from `render.yaml` before applying the Blueprint.

### How Render configuration works

| Variable | Source |
| --- | --- |
| `DATABASE_URL` | Injected from the `internlink-db` database |
| `DJANGO_SECRET_KEY` | Generated by Render (`generateValue: true`) |
| `DEBUG` | `False` (set by the Blueprint) |
| `RENDER_EXTERNAL_HOSTNAME` | Injected by Render; added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically |
| `DJANGO_SUPERUSER_*` | Set in `render.yaml`; the password is prompted at creation |

If `DATABASE_URL` is missing while `DEBUG=False` on Render, the app refuses to start with a clear error rather than silently using the ephemeral filesystem.

### Manual Render setup

If you prefer not to use the Blueprint:

| Setting | Value |
| --- | --- |
| Build command | `bash build.sh` |
| Start command | `python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| `DATABASE_URL` | Render PostgreSQL internal connection string |
| `DJANGO_SECRET_KEY` | A long random value |
| `DEBUG` | `False` |
| `PYTHON_VERSION` | `3.12` (or delete this and keep `.python-version`) |
| `DJANGO_SUPERUSER_EMAIL` | `admin@internlink.test` |
| `DJANGO_SUPERUSER_PASSWORD` | A strong password |

### Render free-tier limitations

- Free web services spin down after 15 minutes of inactivity and take about a minute to wake up.
- Free PostgreSQL databases **expire 30 days after creation**. Upgrade the database, or point `DATABASE_URL` at a free PostgreSQL provider such as Neon for longer-term hosting.
- Free services have an ephemeral filesystem. Uploaded resumes in `media/` are lost on redeploy. Set the optional S3 variables below for permanent uploads.
- For a persistent production deployment, use a paid web service, a paid database, and object storage.

### Permanent file uploads

Render's filesystem is ephemeral. To keep uploaded resumes, set these on the web service; `django-storages` activates automatically when `AWS_STORAGE_BUCKET_NAME` is present:

| Variable | Example |
| --- | --- |
| `AWS_STORAGE_BUCKET_NAME` | `internlink-media` |
| `AWS_ACCESS_KEY_ID` | Storage access key |
| `AWS_SECRET_ACCESS_KEY` | Storage secret key |
| `AWS_S3_ENDPOINT_URL` | `https://ACCOUNT_ID.r2.cloudflarestorage.com` for Cloudflare R2 |
| `AWS_S3_REGION_NAME` | `auto` for R2, or your region |
| `AWS_QUERYSTRING_AUTH` | `True` for private resumes |
| `AWS_S3_ADDRESSING_STYLE` | `virtual` or `path` |

### Other hosting options

- **Railway** — create a Python service and PostgreSQL database, then use the included `Procfile` and set the same environment variables.
- **PythonAnywhere** — works well with SQLite for a small academic deployment; configure a manual WSGI app and run `collectstatic`.
- **VPS (DigitalOcean, Linode, AWS EC2)** — use Nginx + Gunicorn + PostgreSQL, and serve media through Nginx or object storage.

## Use it as a mobile app (iOS and Android)

The site ships as a **Progressive Web App (PWA)**. It installs to a phone home screen, launches full screen with no browser address bar, and updates automatically whenever you deploy. No app store and no second codebase.

### What is included

| Piece | Location |
| --- | --- |
| Web app manifest | `static/manifest.json` |
| Service worker | `templates/pwa/sw.js`, served at `/sw.js` |
| Offline fallback page | `templates/pwa/offline.html` |
| Icons (192, 512, maskable, Apple touch) | `static/icons/` |
| Install button and iOS hint | `static/js/pwa.js` |
| Icon generator | `tools/make_icons.py` |

The service worker caches only public static assets and an offline page. Private HTML is never cached, so signing out cannot expose another user's pages.

### Install on Android

1. Open the deployed site in Chrome.
2. Tap the **⋮** menu → **Install app** (or **Add to Home screen**).
3. Confirm. The InternLink icon appears in the app drawer and opens full screen.

Chrome also shows the **Install app** button in the site navbar once the app is installable.

### Install on iPhone and iPad

1. Open the site in **Safari**. iOS only installs from Safari, not Chrome.
2. Tap **Share** → **Add to Home Screen** → **Add**.
3. Launch it from the home screen.

iOS visitors see a one-time hint bar with these steps; it can be dismissed.

### Regenerate the icons

```bash
python tools/make_icons.py
```

The script uses only the standard library, so it works without Pillow installed.

### Limits of the PWA route

- The site must be served over HTTPS. Render provides this automatically.
- The app is shared by link, not listed in the App Store or Google Play.
- Web push on iOS requires iOS 16.4 or newer and an installed app.
- Offline support is limited to an offline page; applications cannot be submitted offline.

## Publish to the App Store and Google Play

If you need store listings, wrap the same site with **Capacitor**. It loads your deployed Django app inside a native shell, so there is still only one codebase.

Requirements: Node.js, Android Studio for Android, and Xcode on macOS for iOS.

```bash
npm install --save-dev @capacitor/cli @capacitor/core @capacitor/android @capacitor/ios
npx cap init "InternLink" com.yourname.internlink --web-dir=www
```

Create `capacitor.config.json`:

```json
{
  "appId": "com.yourname.internlink",
  "appName": "InternLink",
  "webDir": "www",
  "server": {
    "url": "https://YOUR-SERVICE.onrender.com",
    "cleartext": false
  }
}
```

Then:

```bash
mkdir www
npx cap add android
npx cap add ios
npx cap sync
npx cap open android
npx cap open ios
```

Build and sign the app in Android Studio or Xcode, then upload it to the Play Console or App Store Connect.

### Store requirements to plan for

- **Google Play**: one-time $25 developer registration fee, a privacy policy URL, and a data-safety form.
- **Apple**: $99/year Apple Developer Program and a Mac for builds.
- **Apple guideline 4.2** rejects apps that are only a repackaged website. Add native value first — push notifications, offline application drafts, or camera-based resume upload.
- Both stores require accurate screenshots, descriptions, and a support contact.

## Native app (most work, best experience)

A fully native client is the long-term option:

1. Add Django REST Framework with token or JWT authentication.
2. Expose postings, applications, notifications, and profiles as JSON endpoints.
3. Build the client in Flutter or React Native.

The existing server-rendered views keep working; the API is additive. Budget weeks rather than days — the PWA path above is already working today.

## Troubleshooting

### "403 Forbidden" when logging in or signing up on a phone

This is Django's CSRF protection, not a login bug. The browser did not send the
security cookie that proves the form came from this site. The app logs the exact
reason under `internlink.security`, for example:

```
CSRF failure on POST /accounts/login/: CSRF cookie not set. | hint=cookies ...
```

Common causes and fixes:

| Cause | Fix |
| --- | --- |
| Page opened inside Messenger, Instagram, Facebook, or Gmail | Use the app's "open in browser" option, then retry in Chrome or Safari |
| Private / incognito tab, or cookies blocked | Allow cookies for the site, or leave private mode |
| Site opened over `http://` | Use the `https://` address — `Secure` cookies are dropped on plain HTTP |
| Stale tab left open for a long time | Reload the page before submitting |
| Custom domain not in the trusted list | Add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` |

Any host listed in `ALLOWED_HOSTS` is automatically trusted as an HTTPS origin,
so custom domains work without extra configuration.

### "403" only inside the installed home-screen app

Run the built-in check from inside the app: open `/support/diagnostics/` (or tap
**Run the connection check** on the error page). It reports the host, the
cookies the app sent, the `Origin`/`Referer` headers, and offers a test form.

- **Test form accepted** → the app can submit forms; retry the login.
- **CSRF cookie received: No** or the test form also 403s → the app has no cookie
  storage. This happens when the icon was added from a chat app's in-app
  browser (WhatsApp, Messenger, Instagram, Facebook, Gmail). Fix: delete the
  home-screen icon, open the site in **Chrome** or **Safari**, log in there, then
  add it to the home screen again.

The failure page shows the technical reason under **Technical details**.

## Production notes

Before deploying:

1. Set a strong `DJANGO_SECRET_KEY`.
2. Set `DEBUG=False`.
3. Set `ALLOWED_HOSTS` to your real domains (Render sets `RENDER_EXTERNAL_HOSTNAME` automatically).
4. Use PostgreSQL or another production database instead of SQLite by setting `DATABASE_URL`.
5. Configure a real email backend (the default is the console backend).
6. Run `python manage.py collectstatic`; WhiteNoise serves the collected static files.
7. Enable HTTPS and secure cookies (secure cookies are already toggled when `DEBUG=False`).
8. Serve uploaded media from a persistent, backed-up location.

## License

This project was built as a standalone academic/portfolio system. Add a license of your choice before public distribution.
