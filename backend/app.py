import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


ROOT = Path(__file__).resolve().parent.parent
DATABASE = Path(
    os.environ.get(
        "DATABASE_PATH",
        Path(__file__).resolve().parent / "instance" / "northstar.db",
    )
)
PAGE_ROLES = {
    "overview": {"admin"},
    "staff": {"admin", "staff"},
    "students": {"admin", "staff", "student"},
}
ROLE_PAGES = {
    "admin": ["overview", "staff", "students"],
    "staff": ["staff", "students"],
    "student": ["students"],
}
DEMO_ACCOUNTS = {
    "admin": {"email": "admin@example.com", "password": ""},
    "staff": {"email": "staff1@example.com", "password": ""},
    "student": {"email": "student1@example.com", "password": ""},
}
STUDENT_ROSTER = [
    ("Student One", "DEMO-2026-001", "Computer Science", "Year 2", "student1@example.com", 96, 91, "Active"),
    ("Student Two", "DEMO-2026-002", "Computer Science", "Year 1", "student2@example.com", 91, 87, "Active"),
    ("Student Three", "DEMO-2026-003", "Computer Science", "Year 2", "student3@example.com", 98, 95, "Active"),
    ("Student Four", "DEMO-2026-004", "Computer Science", "Year 4", "student4@example.com", 84, 76, "Review"),
    ("Student Five", "DEMO-2026-005", "Computer Science", "Year 3", "student5@example.com", 93, 89, "Active"),
]
STAFF_ROSTER = [
    ("Staff One", "Department Head", "Computer Science", "staff1@example.com", "Available"),
    ("Staff Two", "Assistant Professor", "Computer Science", "staff2@example.com", "Available"),
    ("Staff Three", "Lecturer", "Computer Science", "staff3@example.com", "On campus"),
    ("Staff Four", "Student Advisor", "Computer Science", "staff4@example.com", "Available"),
]
PRODUCTION_ACCOUNTS = [
    ("admin", "ADMIN_NAME", "ADMIN_EMAIL", "ADMIN_PASSWORD"),
    ("staff", "STAFF_NAME", "STAFF_EMAIL", "STAFF_PASSWORD"),
    ("staff", "STAFF_2_NAME", "STAFF_2_EMAIL", "STAFF_2_PASSWORD"),
    ("staff", "STAFF_3_NAME", "STAFF_3_EMAIL", "STAFF_3_PASSWORD"),
    ("staff", "STAFF_4_NAME", "STAFF_4_EMAIL", "STAFF_4_PASSWORD"),
    ("student", "STUDENT_NAME", "STUDENT_EMAIL", "STUDENT_PASSWORD"),
    ("student", "STUDENT_2_NAME", "STUDENT_2_EMAIL", "STUDENT_2_PASSWORD"),
    ("student", "STUDENT_3_NAME", "STUDENT_3_EMAIL", "STUDENT_3_PASSWORD"),
    ("student", "STUDENT_4_NAME", "STUDENT_4_EMAIL", "STUDENT_4_PASSWORD"),
    ("student", "STUDENT_5_NAME", "STUDENT_5_EMAIL", "STUDENT_5_PASSWORD"),
]
LEGACY_STUDENT_IDS = (
    "LEGACY-STUDENT-1",
    "LEGACY-STUDENT-2",
    "LEGACY-STUDENT-3",
    "LEGACY-STUDENT-4",
    "LEGACY-STUDENT-5",
    "LEGACY-STUDENT-6",
)
LEGACY_STAFF_NAMES = ("Legacy Staff One", "Legacy Staff Two", "Legacy Staff Three")
LEGACY_USER_EMAILS = {
    "staff": "legacy-staff@example.com",
    "student": "legacy-student@example.com",
}

app = Flask(
    __name__,
    template_folder=str(ROOT / "frontend" / "templates"),
    static_folder=str(ROOT / "frontend" / "static"),
)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "development-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    DEMO_MODE=os.environ.get("FLASK_ENV") != "production",
)


def get_db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate_nnct_roster(db):
    if db.execute(
        "SELECT 1 FROM app_meta WHERE key = 'nnct_roster_v1'"
    ).fetchone():
        return

    for role, old_email, roster in (
        ("staff", LEGACY_USER_EMAILS["staff"], STAFF_ROSTER),
        ("student", LEGACY_USER_EMAILS["student"], STUDENT_ROSTER),
    ):
        account = db.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?) AND role = ?",
            (old_email, role),
        ).fetchone()
        if account is not None:
            name, email = roster[0][0], roster[0][3] if role == "staff" else roster[0][4]
            db.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, account["id"]),
            )

    db.execute("UPDATE users SET name = 'Administrator' WHERE role = 'admin'")

    legacy_ids = ",".join("?" for _ in LEGACY_STUDENT_IDS)
    db.execute(
        f"DELETE FROM students WHERE student_id IN ({legacy_ids})",
        LEGACY_STUDENT_IDS,
    )
    db.executemany(
        """INSERT OR IGNORE INTO students
           (name, student_id, program, year, email, attendance, marks, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        STUDENT_ROSTER,
    )

    legacy_staff = db.execute(
        "SELECT id, name FROM staff WHERE name IN (?, ?, ?) ORDER BY id",
        LEGACY_STAFF_NAMES,
    ).fetchall()
    for index, member in enumerate(legacy_staff):
        if index >= len(STAFF_ROSTER):
            break
        name, title, department, email, status = STAFF_ROSTER[index]
        db.execute(
            """UPDATE staff SET name = ?, title = ?, department = ?, email = ?, status = ?
               WHERE id = ?""",
            (name, title, department, email, status, member["id"]),
        )
    for name, title, department, email, status in STAFF_ROSTER:
        db.execute(
            """INSERT INTO staff (name, title, department, email, status)
               SELECT ?, ?, ?, ?, ?
               WHERE NOT EXISTS (SELECT 1 FROM staff WHERE lower(email) = lower(?))""",
            (name, title, department, email, status, email),
        )

    for role, name, email, password in [
        (
            "staff",
            name,
            email,
            account_password("staff", email),
        )
        for name, _title, _department, email, _status in STAFF_ROSTER
    ] + [
        (
            "student",
            name,
            email,
            account_password("student", email),
        )
        for name, _student_id, _program, _year, email, _attendance, _marks, _status in STUDENT_ROSTER
    ]:
        account = db.execute(
            "SELECT id, role FROM users WHERE lower(email) = lower(?)", (email,)
        ).fetchone()
        if account is None:
            db.execute(
                "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, ?, ?)",
                (name, email, role, generate_password_hash(password)),
            )
        elif account["role"] != role:
            raise RuntimeError(f"The roster email {email} is already used by another role.")
        else:
            db.execute(
                "UPDATE users SET name = ? WHERE id = ?", (name, account["id"])
            )

    db.execute(
        "INSERT INTO app_meta (key, value) VALUES ('nnct_roster_v1', 'complete')"
    )


def account_password(role, email):
    if app.config["DEMO_MODE"]:
        password = os.environ.get("DEMO_PASSWORD")
        if password:
            return password
        raise RuntimeError(
            "Set DEMO_PASSWORD to a private local development password before initializing the demo database."
        )

    for configured_role, _name_key, email_key, password_key in PRODUCTION_ACCOUNTS:
        configured_email = os.environ.get(email_key, "").strip().lower()
        if configured_role == role and configured_email == email.lower():
            password = os.environ.get(password_key)
            if password:
                return password
            break
    raise RuntimeError(
        f"Missing production password configuration for the {role} roster account {email}."
    )


def initialize_database():
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'student')),
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_id TEXT NOT NULL UNIQUE,
                program TEXT NOT NULL,
                year TEXT NOT NULL,
                email TEXT NOT NULL,
                attendance INTEGER NOT NULL,
                marks INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                department TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                due_date TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        student_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(students)")
        }
        if "marks" not in student_columns:
            db.execute(
                "ALTER TABLE students ADD COLUMN marks INTEGER NOT NULL DEFAULT 0"
            )
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            if app.config["DEMO_MODE"]:
                initial_users = [
                    (
                        "Administrator",
                        DEMO_ACCOUNTS["admin"]["email"],
                        "admin",
                        account_password("admin", DEMO_ACCOUNTS["admin"]["email"]),
                    ),
                    *[
                        (name, email, "staff", account_password("staff", email))
                        for name, _title, _department, email, _status in STAFF_ROSTER
                    ],
                    *[
                        (name, email, "student", account_password("student", email))
                        for name, _student_id, _program, _year, email, _attendance, _marks, _status in STUDENT_ROSTER
                    ],
                ]
            else:
                missing = [
                    variable
                    for _, _, email_key, password_key in PRODUCTION_ACCOUNTS
                    for variable in (email_key, password_key)
                    if not os.environ.get(variable)
                ]
                if missing:
                    raise RuntimeError(
                        "Missing required production login settings: "
                        + ", ".join(missing)
                    )
                initial_users = [
                    (
                        os.environ.get(name_key, f"NNCT {role.title()}"),
                        os.environ[email_key],
                        role,
                        os.environ[password_key],
                    )
                    for role, name_key, email_key, password_key in PRODUCTION_ACCOUNTS
                ]
            db.executemany(
                "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, ?, ?)",
                [
                    (name, email.strip().lower(), role, generate_password_hash(password))
                    for name, email, role, password in initial_users
                ],
            )

        if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            db.executemany(
                """INSERT INTO students
                   (name, student_id, program, year, email, attendance, marks, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                STUDENT_ROSTER,
            )

        if db.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
            db.executemany(
                """INSERT INTO staff (name, title, department, email, status)
                   VALUES (?, ?, ?, ?, ?)""",
                STAFF_ROSTER,
            )
        migrate_nnct_roster(db)
        db.commit()


def authenticated_user(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return jsonify(error="Please sign in to continue."), 401
        user = get_db().execute(
            "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            session.clear()
            return jsonify(error="Your session is no longer valid. Please sign in again."), 401
        g.user = dict(user)
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorate(view):
        @authenticated_user
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                return jsonify(error="You don't have permission to perform this action."), 403
            return view(*args, **kwargs)

        return wrapped

    return decorate


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None, (jsonify(error="A valid JSON request body is required."), 400)
    return body, None


def required_text(body, field, label):
    value = body.get(field)
    if not isinstance(value, str) or not value.strip():
        return None, (jsonify(error=f"{label} is required."), 400)
    return value.strip(), None


def valid_email(value):
    return len(value) <= 254 and "@" in value and "." in value.rsplit("@", 1)[-1]


def validate_new_account(body):
    fields = {}
    for key, label in (
        ("name", "Name"),
        ("email", "Email"),
        ("password", "Password"),
    ):
        fields[key], error = required_text(body, key, label)
        if error:
            return None, error
    fields["email"] = fields["email"].lower()
    if not valid_email(fields["email"]):
        return None, (jsonify(error="Enter a valid email address."), 400)
    if len(fields["password"]) < 8:
        return None, (jsonify(error="Password must be at least 8 characters."), 400)
    return fields, None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/session")
def session_info():
    demo_credentials = None
    if app.config["DEMO_MODE"]:
        demo_credentials = {
            role: dict(credentials) for role, credentials in DEMO_ACCOUNTS.items()
        }
        current_admin = get_db().execute(
            "SELECT email FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ).fetchone()
        if current_admin is not None:
            admin_email = current_admin["email"]
            if admin_email.lower() != DEMO_ACCOUNTS["admin"]["email"].lower():
                demo_credentials["admin"] = {"email": admin_email, "password": ""}
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify(authenticated=False, demo_credentials=demo_credentials)
    user_row = get_db().execute(
        "SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user_row is None:
        session.clear()
        return jsonify(authenticated=False, demo_credentials=demo_credentials)
    user = {key: value for key, value in dict(user_row).items() if key != "id"}
    user["allowed_pages"] = ROLE_PAGES[user["role"]]
    return jsonify(
        authenticated=True,
        user=user,
        demo_credentials=demo_credentials,
    )


@app.post("/api/login")
def login():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Enter your email and password."), 400
    email = body.get("email")
    password = body.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify(error="Enter your email and password."), 400

    user = get_db().execute(
        "SELECT id, name, email, role, password_hash FROM users WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(error="That email and password combination wasn't recognized."), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify(
        authenticated=True,
        user={
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "allowed_pages": ROLE_PAGES[user["role"]],
        },
    )


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(authenticated=False)


@app.post("/api/students")
@roles_required("admin")
def create_student():
    body, error = json_body()
    if error:
        return error
    account, error = validate_new_account(body)
    if error:
        return error
    student_id, error = required_text(body, "student_id", "Student ID")
    if error:
        return error
    program, error = required_text(body, "program", "Program")
    if error:
        return error
    year, error = required_text(body, "year", "Year")
    if error:
        return error

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, 'student', ?)",
            (account["name"], account["email"], generate_password_hash(account["password"])),
        )
        student_cursor = db.execute(
            """INSERT INTO students
               (name, student_id, program, year, email, attendance, marks, status)
               VALUES (?, ?, ?, ?, ?, 0, 0, 'Active')""",
            (account["name"], student_id, program, year, account["email"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error="That email or student ID is already in use."), 409
    return jsonify(id=student_cursor.lastrowid, message="Student and student login created."), 201


@app.delete("/api/students/<int:student_id>")
@roles_required("admin")
def delete_student(student_id):
    db = get_db()
    student = db.execute(
        "SELECT email FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    if student is None:
        return jsonify(error="Student not found."), 404
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.execute(
        "DELETE FROM users WHERE lower(email) = lower(?) AND role = 'student'",
        (student["email"],),
    )
    db.commit()
    return jsonify(message="Student and student login deleted.")


@app.patch("/api/students/<int:student_id>")
@roles_required("admin", "staff")
def update_student_record(student_id):
    body, error = json_body()
    if error:
        return error
    updates = {}
    for field in ("marks", "attendance"):
        if field not in body:
            continue
        value = body[field]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            return jsonify(error=f"{field.title()} must be a whole number from 0 to 100."), 400
        updates[field] = value
    if not updates:
        return jsonify(error="Provide marks, attendance, or both to update."), 400

    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE id = ?", (student_id,)).fetchone() is None:
        return jsonify(error="Student not found."), 404
    columns = ", ".join(f"{field} = ?" for field in updates)
    values = list(updates.values())
    if "attendance" in updates:
        columns += ", status = ?"
        values.append("Review" if updates["attendance"] < 85 else "Active")
    values.append(student_id)
    db.execute(f"UPDATE students SET {columns} WHERE id = ?", values)
    db.commit()
    student = db.execute(
        "SELECT marks, attendance, status FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    return jsonify(student=dict(student), message="Student record updated.")


@app.post("/api/staff")
@roles_required("admin")
def create_staff_member():
    body, error = json_body()
    if error:
        return error
    account, error = validate_new_account(body)
    if error:
        return error
    title, error = required_text(body, "title", "Job title")
    if error:
        return error
    department, error = required_text(body, "department", "Department")
    if error:
        return error

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, 'staff', ?)",
            (account["name"], account["email"], generate_password_hash(account["password"])),
        )
        cursor = db.execute(
            """INSERT INTO staff (name, title, department, email, status)
               VALUES (?, ?, ?, ?, 'Available')""",
            (account["name"], title, department, account["email"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify(error="That email address is already in use."), 409
    return jsonify(id=cursor.lastrowid, message="Staff member and login created."), 201


@app.delete("/api/staff/<int:staff_id>")
@roles_required("admin")
def delete_staff_member(staff_id):
    db = get_db()
    member = db.execute(
        "SELECT email FROM staff WHERE id = ?", (staff_id,)
    ).fetchone()
    if member is None:
        return jsonify(error="Staff member not found."), 404
    db.execute("DELETE FROM assignments WHERE staff_id = ?", (staff_id,))
    db.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    db.execute(
        "DELETE FROM users WHERE lower(email) = lower(?) AND role = 'staff'",
        (member["email"],),
    )
    db.commit()
    return jsonify(message="Staff member and their assignments deleted.")


@app.post("/api/assignments")
@roles_required("admin")
def create_assignment():
    body, error = json_body()
    if error:
        return error
    title, error = required_text(body, "title", "Work title")
    if error:
        return error
    description = body.get("description", "")
    due_date = body.get("due_date", "")
    if not isinstance(description, str) or not isinstance(due_date, str):
        return jsonify(error="Description and due date must be text."), 400
    staff_id = body.get("staff_id")
    if isinstance(staff_id, bool) or not isinstance(staff_id, int):
        return jsonify(error="Choose a staff member for this assignment."), 400
    db = get_db()
    if db.execute("SELECT 1 FROM staff WHERE id = ?", (staff_id,)).fetchone() is None:
        return jsonify(error="That staff member was not found."), 404
    cursor = db.execute(
        """INSERT INTO assignments (staff_id, title, description, due_date)
           VALUES (?, ?, ?, ?)""",
        (staff_id, title, description.strip(), due_date.strip()),
    )
    db.commit()
    return jsonify(id=cursor.lastrowid, message="Work assigned to staff member."), 201


@app.get("/api/dashboard")
@authenticated_user
def dashboard():
    page = request.args.get("page", "")
    if page not in PAGE_ROLES or g.user["role"] not in PAGE_ROLES[page]:
        return jsonify(error="You don't have permission to view this page."), 403

    db = get_db()
    students = db.execute(
        "SELECT id, name, student_id, program, year, email, attendance, marks, status "
        "FROM students ORDER BY name"
    ).fetchall()
    staff = db.execute(
        "SELECT id, name, title, department, email, status FROM staff ORDER BY name"
    ).fetchall()
    if g.user["role"] == "student":
        students = [row for row in students if row["email"].lower() == g.user["email"].lower()]
    average_attendance = round(
        sum(row["attendance"] for row in students) / len(students)
    ) if students else 0
    average_marks = round(
        sum(row["marks"] for row in students) / len(students)
    ) if students else 0

    if page == "overview":
        metrics = [
            {"label": "Total students", "value": len(students), "change": "+12.8%", "icon": "users", "tone": "violet"},
            {"label": "Faculty members", "value": len(staff), "change": "+2 this term", "icon": "briefcase", "tone": "blue"},
            {"label": "Average attendance", "value": f"{average_attendance}%", "change": "Live student records", "icon": "activity", "tone": "green"},
            {"label": "Average marks", "value": f"{average_marks}%", "change": "Live student records", "icon": "trend", "tone": "amber"},
        ]
    elif page == "staff":
        metrics = [
            {"label": "Faculty members", "value": len(staff), "change": "Across 3 departments", "icon": "briefcase", "tone": "violet"},
            {"label": "Students supported", "value": db.execute("SELECT COUNT(*) FROM students").fetchone()[0], "change": "Across all programs", "icon": "users", "tone": "blue"},
            {"label": "Average attendance", "value": f"{average_attendance}%", "change": "Live student records", "icon": "activity", "tone": "green"},
        ]
    elif g.user["role"] == "student":
        current_student = students[0] if students else None
        metrics = [
            {"label": "Your program", "value": current_student["program"] if current_student else "Not assigned", "change": f"{current_student['year']} · Your program" if current_student else "Contact your administrator", "icon": "book", "tone": "violet"},
            {"label": "Attendance", "value": f"{current_student['attendance']}%" if current_student else "—", "change": "Updated by your staff", "icon": "activity", "tone": "green"},
            {"label": "Your marks", "value": f"{current_student['marks']}%" if current_student else "—", "change": "Updated by your staff", "icon": "trend", "tone": "amber"},
            {"label": "Courses this term", "value": "5", "change": "2 classes today", "icon": "book", "tone": "blue"},
        ]
    else:
        metrics = [
            {"label": "Total students", "value": len(students), "change": "In the student directory", "icon": "users", "tone": "violet"},
            {"label": "Average attendance", "value": f"{average_attendance}%", "change": "Live student records", "icon": "activity", "tone": "green"},
            {"label": "Average marks", "value": f"{average_marks}%", "change": "Live student records", "icon": "trend", "tone": "blue"},
        ]
    if page == "staff":
        assignment_query = """SELECT assignments.id, assignments.title, assignments.description,
                                    assignments.due_date, staff.name AS staff_name, staff.email
                             FROM assignments JOIN staff ON staff.id = assignments.staff_id"""
        if g.user["role"] == "staff":
            assignments = db.execute(
                assignment_query + " WHERE lower(staff.email) = lower(?) ORDER BY assignments.id DESC",
                (g.user["email"],),
            ).fetchall()
        else:
            assignments = db.execute(
                assignment_query + " ORDER BY assignments.id DESC"
            ).fetchall()
    else:
        assignments = []

    return jsonify(
        page=page,
        metrics=metrics,
        students=[dict(row) for row in students],
        staff=[dict(row) for row in staff],
        assignments=[dict(row) for row in assignments],
        attendance=[78, 84, 80, 91, 86, 94, 89, 96, 88, 93, 90, 97],
        activities=[
            {"initials": "S1", "name": "Student One", "detail": "Submitted a project milestone", "time": "12 min ago", "tone": "violet"},
            {"initials": "S2", "name": "Student Two", "detail": "Attendance updated · CS204", "time": "38 min ago", "tone": "blue"},
            {"initials": "S3", "name": "Student Three", "detail": "Received advisor feedback", "time": "1 hr ago", "tone": "amber"},
        ],
        schedule=[
            {"time": "09:00 AM", "course": "Human-Centered Design", "room": "Studio 204", "tone": "violet"},
            {"time": "11:30 AM", "course": "Data Structures", "room": "Lecture Hall A", "tone": "blue"},
            {"time": "02:00 PM", "course": "Research Methods", "room": "Seminar 3", "tone": "green"},
        ],
    )


initialize_database()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
