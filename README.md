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
├── static/            # Project CSS and assets
├── templates/         # Shared and app templates
├── manage.py
├── requirements.txt
├── build.sh            # Render build script
├── Procfile            # Gunicorn start command
├── render.yaml         # Render Blueprint (web service + Postgres)
├── vercel.json         # Vercel build/function configuration
├── .vercelignore       # Files excluded from Vercel uploads
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

## Deploy to Render (recommended)

The repository includes a `render.yaml` Blueprint, `build.sh`, and `Procfile`, so Render can deploy the project directly from GitHub.

1. Push the project to GitHub.
2. Sign in at <https://dashboard.render.com/>.
3. Choose **New → Blueprint**.
4. Connect your GitHub repository.
5. Apply the Blueprint. Render creates:
   - a free Python web service running Gunicorn
   - a free PostgreSQL database
6. Wait for the build to finish. The app is live at the `.onrender.com` URL shown in the dashboard.

Render injects `RENDER_EXTERNAL_HOSTNAME`, `DATABASE_URL`, and the generated `DJANGO_SECRET_KEY`. `DEBUG` is set to `False` by the Blueprint.

During Blueprint creation, Render prompts for `DJANGO_SUPERUSER_PASSWORD`. Enter a strong password for the admin account. The Blueprint also sets:

- `DJANGO_SUPERUSER_EMAIL=admin@internlink.test`
- `DJANGO_SUPERUSER_FIRST_NAME=Portal`
- `DJANGO_SUPERUSER_LAST_NAME=Admin`

### First deploy initialization

The `build.sh` script runs migrations and `python manage.py bootstrap`, which creates or updates the admin superuser from the environment variables.

The Blueprint's `initialDeployHook` runs once after the first successful deploy:

```bash
python manage.py bootstrap --seed
```

This creates the admin account and loads the demo dataset. After deployment, log in at:

```
https://YOUR-SERVICE.onrender.com/admin/
```

Use `admin@internlink.test` and the password you entered during Blueprint creation. The demo accounts use `demo12345`.

If you prefer no demo data, remove the `initialDeployHook` line from `render.yaml` before applying the Blueprint.

### Manual initialization

If you are not using the Blueprint, set these environment variables on the service:

| Variable | Value |
| --- | --- |
| `DJANGO_SUPERUSER_EMAIL` | `admin@internlink.test` |
| `DJANGO_SUPERUSER_PASSWORD` | A strong password |
| `DJANGO_SUPERUSER_FIRST_NAME` | `Portal` |
| `DJANGO_SUPERUSER_LAST_NAME` | `Admin` |

Then run once from the Render Shell (paid plans) or locally against the production database:

```bash
python manage.py bootstrap --seed
```

### Render free-tier limitations

- Free web services spin down after 15 minutes of inactivity and take about a minute to wake up.
- Free PostgreSQL databases expire 30 days after creation. Upgrade the database or use a free PostgreSQL provider such as Neon for longer-term hosting.
- Free services have an ephemeral filesystem. Uploaded resumes in `media/` are lost on redeploy. Use Cloudinary, S3, or another object store for permanent uploads.
- For a persistent production deployment, use a paid web service, a paid database, and object storage.

### Manual Render setup

If you prefer not to use the Blueprint:

| Setting | Value |
| --- | --- |
| Build command | `bash build.sh` |
| Start command | `python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |
| `DATABASE_URL` | Render PostgreSQL internal connection string |
| `DJANGO_SECRET_KEY` | A long random value |
| `DEBUG` | `False` |
| `PYTHON_VERSION` | `3.12.6` |
| `DJANGO_SUPERUSER_EMAIL` | `admin@internlink.test` |
| `DJANGO_SUPERUSER_PASSWORD` | A strong password |

## Deploy to Vercel

Vercel now supports Django with zero configuration. The repository includes `vercel.json`, and Vercel detects `manage.py` and `config/wsgi.py` automatically.

Vercel Functions have a read-only, ephemeral filesystem, so this app **cannot use SQLite or local media storage in production**. Before deploying, create:

1. **PostgreSQL database** — Neon, Supabase, or Vercel's Postgres integration.
2. **S3-compatible object storage** — Cloudflare R2, Supabase Storage, Backblaze B2, or AWS S3, for uploaded resumes.

The project includes optional S3 storage support through `django-storages`. It activates automatically when `AWS_STORAGE_BUCKET_NAME` is set.

### 1. Install and log in to the Vercel CLI

```bash
npm install -g vercel
vercel login
```

Or use `npx vercel` instead of a global install.

### 2. Link the project

```bash
cd "C:\Users\Lenovo\Documents\Default Project\internship_portal"
vercel link
```

Choose **Create a new project** and accept the detected settings.

### 3. Add environment variables

Add these in **Vercel → Project → Settings → Environment Variables**, or with `vercel env add`:

| Variable | Required | Example |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Yes | A long random string |
| `DEBUG` | Yes | `False` |
| `DATABASE_URL` | Yes | `postgresql://user:pass@host/db?sslmode=require` |
| `DJANGO_SUPERUSER_EMAIL` | Yes | `admin@internlink.test` |
| `DJANGO_SUPERUSER_PASSWORD` | Yes | A strong password |
| `DJANGO_SUPERUSER_FIRST_NAME` | No | `Portal` |
| `DJANGO_SUPERUSER_LAST_NAME` | No | `Admin` |
| `AWS_STORAGE_BUCKET_NAME` | Yes | `internlink-media` |
| `AWS_ACCESS_KEY_ID` | Yes | Storage access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | Storage secret key |
| `AWS_S3_ENDPOINT_URL` | For R2/Supabase | `https://ACCOUNT_ID.r2.cloudflarestorage.com` |
| `AWS_S3_REGION_NAME` | For R2/Supabase | `auto` or your region |
| `AWS_QUERYSTRING_AUTH` | No | `True` for private resumes |
| `AWS_S3_ADDRESSING_STYLE` | No | `virtual` or `path` |

Vercel automatically provides `VERCEL_URL` and `VERCEL_PROJECT_PRODUCTION_URL`; the app adds them to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### 4. Deploy

```bash
vercel --prod
```

The `vercel.json` build command runs:

```bash
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py bootstrap
```

This creates the admin account from the environment variables. Demo data is **not** loaded automatically on Vercel. To load it once, set `DATABASE_URL` locally and run:

```bash
python manage.py migrate
python manage.py bootstrap --seed
```

### 5. Log in

Open the deployment URL, then visit:

```
https://YOUR-PROJECT.vercel.app/admin/
```

Use `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`.

### Vercel caveats

- The build command runs migrations against the database on every deployment. Use a separate database for preview deployments if you need isolation.
- Vercel Functions have execution-time and bundle-size limits. The included `maxDuration` is 60 seconds.
- Uploaded resumes must go to S3-compatible storage. Without it, file uploads will fail.
- Vercel is a better fit for the HTTP app than for long-running background jobs or scheduled work.

### Other hosting options

- **Railway** — create a Python service and PostgreSQL database, then use the included `Procfile` and set the same environment variables.
- **PythonAnywhere** — works well with SQLite for a small academic deployment; configure a manual WSGI app and run `collectstatic`.
- **VPS (DigitalOcean, Linode, AWS EC2)** — use Nginx + Gunicorn + PostgreSQL, and serve media through Nginx or object storage.

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
