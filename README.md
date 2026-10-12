# NNCT Student Management System

A role-based NNCT student-management dashboard built with React and Flask.

## Project layout

```text
backend/
  app.py
  requirements.txt
  venv/                 # Create locally; not committed
  instance/             # SQLite database created automatically
frontend/
  templates/
    index.html
  static/
    css/styles.css
    images/logo.svg
    js/app.js
```

## Run locally

From the project root, create and activate the backend virtual environment:

```powershell
python -m venv backend\venv
.\backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$securePassword = Read-Host "Private local demo password" -AsSecureString
$env:DEMO_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
python backend\app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The interface loads React and ReactDOM from the unpkg CDN, so an internet
connection is needed to load the dashboard.

The seeded names, email addresses, student IDs, and academic records are
fictional sample data. Set a private `DEMO_PASSWORD` environment variable before
first running the app; all seeded local demo accounts use it. The demo email
addresses are shown on the sign-in page; no password is shipped in the source
or returned by the API. Production mode disables demo accounts and requires
separate account passwords from environment variables.

## Deploy on Render

The root-level `render.yaml` configures a sample Render web service with
Gunicorn, a generated session secret, sample-only account identities, and a
persistent disk for the SQLite database. Create a GitHub repository, push this
project, then create a Render Blueprint from that repository. The blueprint
generates separate account passwords; configure real account identities and
find the generated passwords in Render's environment settings after the service
is created. Render assigns the deployed service its public URL.

The persistent database disk may require a paid Render plan. Replace all sample
account identities with authorized account details before launch.

## Access levels

- Admin: overview, staff directory, and student directory; can create/delete staff and students, assign work to staff, and update student marks and attendance.
- Staff: staff and student directories; can update marks and attendance and view work assigned to their account.
- Student: their own student record, including the latest marks and attendance, in read-only mode.

Page and data-change permissions are enforced by the Flask API as well as by
the interface. New student and staff accounts can sign in with the password
set by the administrator when creating the account.

## Tests

```powershell
backend\venv\Scripts\python.exe -m unittest discover -s backend -p test_app.py -v
```

## Public source repository

The repository contains fictional sample records only. Do not commit the local
SQLite database, virtual environment, real student or staff data, or secrets.
GitHub Pages cannot run this Flask backend; use a Python-capable host such as
Render to publish a live website.
