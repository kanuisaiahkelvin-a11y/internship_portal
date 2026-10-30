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

### After the first deploy

Open the Render **Shell** for the web service and create an admin account:

```bash
python manage.py createsuperuser
```

Optionally load the demo data once:

```bash
python manage.py seed_demo
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
