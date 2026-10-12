import os
import secrets
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("DEMO_PASSWORD", secrets.token_urlsafe(24))

import app as application


class StudentManagementTests(unittest.TestCase):
    def setUp(self):
        self.database_dir = tempfile.TemporaryDirectory()
        self.previous_demo_password = os.environ.get("DEMO_PASSWORD")
        os.environ["DEMO_PASSWORD"] = secrets.token_urlsafe(24)
        application.DATABASE = Path(self.database_dir.name) / "test.db"
        application.app.config.update(
            TESTING=True,
            DEMO_MODE=True,
            SECRET_KEY=secrets.token_urlsafe(32),
        )
        application.initialize_database()
        self.client = application.app.test_client()

    def tearDown(self):
        self.client = None
        self.database_dir.cleanup()
        if self.previous_demo_password is None:
            os.environ.pop("DEMO_PASSWORD", None)
        else:
            os.environ["DEMO_PASSWORD"] = self.previous_demo_password

    def login(self, role):
        credentials = application.DEMO_ACCOUNTS[role]
        response = self.client.post(
            "/api/login",
            json={**credentials, "password": os.environ["DEMO_PASSWORD"]},
        )
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_nnct_roster_and_all_demo_accounts_are_seeded(self):
        expected_students = [item[0] for item in application.STUDENT_ROSTER]
        expected_staff = [item[0] for item in application.STAFF_ROSTER]
        with application.app.app_context():
            db = application.get_db()
            self.assertEqual(
                [row["name"] for row in db.execute("SELECT name FROM students ORDER BY student_id")],
                expected_students,
            )
            self.assertEqual(
                [row["name"] for row in db.execute("SELECT name FROM staff ORDER BY id")],
                expected_staff,
            )
            for role, name, email in [
                ("staff", item[0], item[3]) for item in application.STAFF_ROSTER
            ] + [
                ("student", item[0], item[4]) for item in application.STUDENT_ROSTER
            ]:
                user = db.execute(
                    "SELECT name, role FROM users WHERE email = ?", (email,)
                ).fetchone()
                self.assertEqual((user["name"], user["role"]), (name, role))

    def test_nnct_migration_preserves_admin_custom_records_and_assignments(self):
        with application.app.app_context():
            db = application.get_db()
            admin = db.execute(
                "SELECT email, password_hash FROM users WHERE role = 'admin'"
            ).fetchone()
            staff_id = db.execute(
                "SELECT id FROM staff WHERE name = ?",
                (application.STAFF_ROSTER[0][0],),
            ).fetchone()["id"]

            db.execute("DELETE FROM app_meta WHERE key = 'nnct_roster_v1'")
            db.execute("DELETE FROM students")
            db.executemany(
                """INSERT INTO students
                   (name, student_id, program, year, email, attendance, marks, status)
                   VALUES (?, ?, 'Computer Science', 'Year 1', ?, 90, 80, 'Active')""",
                [
                    (f"Legacy Student {index}", student_id, f"old{index}@example.com")
                    for index, student_id in enumerate(application.LEGACY_STUDENT_IDS)
                ],
            )
            db.execute(
                """INSERT INTO students
                   (name, student_id, program, year, email, attendance, marks, status)
                   VALUES ('Custom Student', 'CUSTOM-1', 'Science', 'Year 1',
                           'custom@example.edu', 90, 80, 'Active')"""
            )
            db.execute(
                "UPDATE users SET email = ? WHERE email = ?",
                (
                    application.LEGACY_USER_EMAILS["student"],
                    application.STUDENT_ROSTER[0][4],
                ),
            )
            db.execute(
                "DELETE FROM users WHERE role = 'student' AND email != ?",
                (application.LEGACY_USER_EMAILS["student"],),
            )

            db.execute(
                "UPDATE staff SET name = ? WHERE id = ?",
                (application.LEGACY_STAFF_NAMES[0], staff_id),
            )
            db.execute(
                "UPDATE staff SET name = ? WHERE name = ?",
                (application.LEGACY_STAFF_NAMES[1], application.STAFF_ROSTER[1][0]),
            )
            db.execute(
                "UPDATE staff SET name = ? WHERE name = ?",
                (application.LEGACY_STAFF_NAMES[2], application.STAFF_ROSTER[2][0]),
            )
            db.execute(
                "DELETE FROM staff WHERE name = ?", (application.STAFF_ROSTER[3][0],)
            )
            db.execute(
                "UPDATE users SET email = ? WHERE email = ?",
                (
                    application.LEGACY_USER_EMAILS["staff"],
                    application.STAFF_ROSTER[0][3],
                ),
            )
            db.execute(
                "DELETE FROM users WHERE role = 'staff' AND email != ?",
                (application.LEGACY_USER_EMAILS["staff"],),
            )
            db.execute(
                "INSERT INTO assignments (staff_id, title) VALUES (?, 'Preserved task')",
                (staff_id,),
            )

            application.migrate_nnct_roster(db)
            db.commit()
            self.assertEqual(
                tuple(db.execute(
                    "SELECT email, password_hash FROM users WHERE role = 'admin'"
                ).fetchone()),
                tuple(admin),
            )
            self.assertEqual(
                db.execute(
                    "SELECT COUNT(*) FROM students WHERE student_id IN (?, ?, ?, ?, ?)",
                    tuple(item[1] for item in application.STUDENT_ROSTER),
                ).fetchone()[0],
                5,
            )
            self.assertEqual(
                db.execute(
                    "SELECT COUNT(*) FROM students WHERE student_id = 'CUSTOM-1'"
                ).fetchone()[0],
                1,
            )
            assignment = db.execute(
                """SELECT assignments.title, staff.name
                   FROM assignments JOIN staff ON staff.id = assignments.staff_id"""
            ).fetchone()
            self.assertEqual(tuple(assignment), ("Preserved task", application.STAFF_ROSTER[0][0]))

            application.migrate_nnct_roster(db)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM students").fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM staff").fetchone()[0], 4)
            db.commit()

    def test_staff_can_update_records_and_student_only_sees_own_results(self):
        student = self.client.get("/api/dashboard?page=students")
        self.assertEqual(student.status_code, 401)

        self.login("staff")
        students = self.client.get("/api/dashboard?page=students").get_json()["students"]
        self.assertEqual(len(students), 5)
        sample_student = next(
            item
            for item in students
            if item["student_id"] == application.STUDENT_ROSTER[0][1]
        )
        response = self.client.patch(
            f"/api/students/{sample_student['id']}",
            json={"marks": 93, "attendance": 82},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["student"]["status"], "Review")
        self.client.post("/api/logout")

        self.login("student")
        result = self.client.get("/api/dashboard?page=students").get_json()["students"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["email"], application.STUDENT_ROSTER[0][4])
        self.assertEqual((result[0]["marks"], result[0]["attendance"]), (93, 82))
        self.assertEqual(
            self.client.patch(
                f"/api/students/{sample_student['id']}",
                json={"marks": 100},
            ).status_code,
            403,
        )

    def test_admin_can_update_marks_and_attendance(self):
        self.login("admin")
        students = self.client.get("/api/dashboard?page=students").get_json()["students"]
        student_id = students[0]["id"]
        response = self.client.patch(
            f"/api/students/{student_id}",
            json={"marks": 88, "attendance": 99},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(
            response.get_json()["student"],
            {"marks": 88, "attendance": 99, "status": "Active"},
        )

    def test_custom_local_admin_email_is_prefilled_without_exposing_password(self):
        with application.app.app_context():
            db = application.get_db()
            admin_id = db.execute(
                "SELECT id FROM users WHERE role = 'admin'"
            ).fetchone()["id"]
            db.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                ("principal@example.edu", admin_id),
            )
            db.commit()

        credentials = self.client.get("/api/session").get_json()["demo_credentials"]
        self.assertEqual(credentials["admin"]["email"], "principal@example.edu")
        self.assertEqual(credentials["admin"]["password"], "")
        self.assertTrue(all(item["password"] == "" for item in credentials.values()))

    def test_admin_can_create_and_delete_student_and_login(self):
        self.login("admin")
        student_password = secrets.token_urlsafe(16)
        response = self.client.post(
            "/api/students",
            json={
                "name": "Priya Shah",
                "student_id": "NS-2026-1001",
                "email": "priya.shah@example.edu",
                "program": "Data Science",
                "year": "Year 1",
                "password": student_password,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        student_id = response.get_json()["id"]
        self.client.post("/api/logout")

        self.assertEqual(
            self.client.post(
                "/api/login",
                json={"email": "priya.shah@example.edu", "password": student_password},
            ).status_code,
            200,
        )
        self.client.post("/api/logout")
        self.login("admin")
        self.assertEqual(
            self.client.delete(f"/api/students/{student_id}").status_code,
            200,
        )
        self.client.post("/api/logout")
        self.assertEqual(
            self.client.post(
                "/api/login",
                json={"email": "priya.shah@example.edu", "password": student_password},
            ).status_code,
            401,
        )

    def test_admin_can_create_assign_and_remove_staff(self):
        self.login("admin")
        staff_password = secrets.token_urlsafe(16)
        existing_staff = self.client.get("/api/dashboard?page=staff").get_json()["staff"]
        staff_id = next(
            item["id"]
            for item in existing_staff
            if item["name"] == application.STAFF_ROSTER[0][0]
        )
        self.assertEqual(
            self.client.post(
                "/api/assignments",
                json={"staff_id": staff_id, "title": "Staff-only task"},
            ).status_code,
            201,
        )
        response = self.client.post(
            "/api/staff",
            json={
                "name": "Priya Shah",
                "email": "priya.staff@example.edu",
                "title": "Science Teacher",
                "department": "Science",
                "password": staff_password,
            },
        )
        self.assertEqual(response.status_code, 201, response.get_json())
        staff_id = response.get_json()["id"]
        assignment = self.client.post(
            "/api/assignments",
            json={
                "staff_id": staff_id,
                "title": "Prepare lab materials",
                "description": "Organize the Year 1 kits.",
                "due_date": "2026-11-01",
            },
        )
        self.assertEqual(assignment.status_code, 201, assignment.get_json())
        self.client.post("/api/logout")

        self.assertEqual(
            self.client.post(
                "/api/login",
                json={"email": "priya.staff@example.edu", "password": staff_password},
            ).status_code,
            200,
        )
        work = self.client.get("/api/dashboard?page=staff").get_json()["assignments"]
        self.assertEqual([item["title"] for item in work], ["Prepare lab materials"])
        self.assertEqual(
            self.client.get("/api/dashboard?page=overview").status_code,
            403,
        )
        self.client.post("/api/logout")
        self.login("admin")
        self.assertEqual(self.client.delete(f"/api/staff/{staff_id}").status_code, 200)
        self.client.post("/api/logout")
        self.assertEqual(
            self.client.post(
                "/api/login",
                json={"email": "priya.staff@example.edu", "password": staff_password},
            ).status_code,
            401,
        )

    def test_only_admin_can_manage_accounts_or_assign_work(self):
        self.login("staff")
        self.assertEqual(
            self.client.post("/api/students", json={}).status_code,
            403,
        )
        self.assertEqual(
            self.client.post("/api/staff", json={}).status_code,
            403,
        )
        self.assertEqual(
            self.client.post("/api/assignments", json={}).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete("/api/students/1").status_code,
            403,
        )

        self.client.post("/api/logout")
        self.login("student")
        self.assertEqual(
            self.client.post("/api/assignments", json={}).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete("/api/staff/1").status_code,
            403,
        )

    def test_marks_and_attendance_are_validated(self):
        self.login("staff")
        student = self.client.get("/api/dashboard?page=students").get_json()["students"][0]
        for value in (-1, 101, 90.5, True):
            response = self.client.patch(
                f"/api/students/{student['id']}",
                json={"marks": value},
            )
            self.assertEqual(response.status_code, 400, response.get_json())
        self.assertEqual(
            self.client.patch(
                f"/api/students/{student['id']}",
                json={},
            ).status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
