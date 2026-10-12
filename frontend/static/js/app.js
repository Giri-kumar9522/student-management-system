(function () {
  "use strict";

  const h = React.createElement;
  const icons = {
    overview: ["M3 3h8v8H3z", "M13 3h8v5h-8z", "M13 10h8v11h-8z", "M3 13h8v8H3z"],
    users: ["M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M20 8v6", "M23 11h-6"],
    briefcase: ["M3 7h18v14H3z", "M8 7V4h8v3", "M3 12h18", "M10 12v2h4v-2"],
    activity: ["M22 12h-4l-3 9L9 3l-3 9H2"],
    trend: ["M3 17l6-6 4 4 8-8", "M15 7h6v6"],
    book: ["M4 19.5A2.5 2.5 0 0 1 6.5 17H20", "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"],
    calendar: ["M8 2v4", "M16 2v4", "M3 10h18", "M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2z"],
    search: ["M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "m21 21-4.35-4.35"],
    bell: ["M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9", "M10 21h4"],
    arrow: ["M5 12h14", "m12 5 7 7-7 7"],
    arrowUp: ["M7 17 17 7", "M7 7h10v10"],
    logout: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "m16 17 5-5-5-5", "M21 12H9"],
    eye: ["M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z", "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"],
    admin: ["M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z", "M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.7 2.9-.2-.1a1.7 1.7 0 0 0-1.8.1 1.7 1.7 0 0 0-.9 1.5v.2H8.8v-.2a1.7 1.7 0 0 0-.9-1.5 1.7 1.7 0 0 0-1.8-.1l-.2.1-1.7-2.9.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.4-1H3v-3.4h.2a1.7 1.7 0 0 0 1.4-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 1.7-2.9.2.1a1.7 1.7 0 0 0 1.8-.1 1.7 1.7 0 0 0 .9-1.5V3h6.4v.2a1.7 1.7 0 0 0 .9 1.5 1.7 1.7 0 0 0 1.8.1l.2-.1 1.7 2.9-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.4 1h.2V14h-.2a1.7 1.7 0 0 0-1.4 1z"],
    shield: ["M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11z", "m9 12 2 2 4-4"],
    student: ["M22 10 12 5 2 10l10 5 10-5z", "M6 12v5c3 3 9 3 12 0v-5", "M22 10v6"],
    clock: ["M12 8v4l3 2", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"],
  };

  function Icon({ name, size = 18, strokeWidth = 1.7 }) {
    const paths = icons[name] || icons.overview;
    return h("svg", { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true },
      paths.map((path, index) => h("path", { d: path, key: index })));
  }

  function initials(name) {
    return name.split(" ").map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  }

  function todayLabel() {
    return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" }).format(new Date());
  }

  async function api(path, options) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options && options.headers) },
      ...options,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Something went wrong.");
    return payload;
  }

  function Login({ onLogin, demoCredentials }) {
    const [role, setRole] = React.useState("admin");
    const [email, setEmail] = React.useState(demoCredentials ? demoCredentials.admin.email : "");
    const [password, setPassword] = React.useState(demoCredentials ? demoCredentials.admin.password : "");
    const [showPassword, setShowPassword] = React.useState(false);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState("");
    function selectRole(nextRole) {
      setRole(nextRole);
      setEmail(demoCredentials ? demoCredentials[nextRole].email : "");
      setPassword(demoCredentials ? demoCredentials[nextRole].password : "");
      setError("");
    }

    async function submit(event) {
      event.preventDefault();
      setLoading(true);
      setError("");
      try {
        const result = await api("/api/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
        onLogin(result.user);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    return h("main", { className: "login-page" },
      h("section", { className: "login-showcase" },
        h("div", { className: "login-brand" },
          h("img", { src: "/static/images/logo.svg", alt: "" }),
          h("span", null, "NNCT")),
        h("div", { className: "showcase-copy" },
          h("div", { className: "showcase-kicker" }, "Your campus, in sync"),
          h("h1", null, "A brighter way to ", h("span", null, "learn.")),
          h("p", null, "One thoughtful space for student success, meaningful connections, and everything that makes your campus move forward.")),
        h("div", { className: "showcase-foot" }, "A more connected campus starts here · NNCT")),
      h("section", { className: "login-form-side" },
        h("form", { className: "login-form-wrap", onSubmit: submit },
          h("h2", null, "Welcome back"),
          h("p", { className: "login-subtitle" }, "Choose your workspace and sign in to continue."),
          h("div", { className: "role-picker", "aria-label": "Choose a role" },
            ["admin", "staff", "student"].map((item) =>
              h("button", {
                type: "button",
                className: `role-option ${role === item ? "selected" : ""}`,
                onClick: () => selectRole(item),
                key: item,
              }, h(Icon, { name: item === "admin" ? "admin" : item === "staff" ? "briefcase" : "student", size: 16 }), item[0].toUpperCase() + item.slice(1)))),
          h("label", { className: "field-label", htmlFor: "email" }, "Email address"),
          h("input", { id: "email", className: "login-input", type: "email", autoComplete: "username", required: true, value: email, onChange: (event) => setEmail(event.target.value) }),
          h("label", { className: "field-label", htmlFor: "password" }, "Password"),
          h("div", { className: "password-wrap" },
            h("input", { id: "password", className: "login-input", type: showPassword ? "text" : "password", autoComplete: "current-password", required: true, value: password, onChange: (event) => setPassword(event.target.value) }),
            h("button", { type: "button", className: "show-password", onClick: () => setShowPassword(!showPassword), "aria-label": showPassword ? "Hide password" : "Show password" }, h(Icon, { name: "eye", size: 16 }))),
          error ? h("p", { className: "login-error", role: "alert" }, error) : null,
          h("button", { className: "submit-button", type: "submit", disabled: loading }, loading ? "Signing you in…" : h(React.Fragment, null, "Sign in to NNCT", h(Icon, { name: "arrow", size: 15 }))),
          demoCredentials ? h("div", { className: "demo-box" },
            h("div", { className: "demo-title" }, "Local demo accounts · set DEMO_PASSWORD"),
            h("div", { className: "demo-details" },
              ["admin", "staff", "student"].map((item) =>
                h("button", { className: "demo-role", type: "button", key: item, onClick: () => selectRole(item) }, item[0].toUpperCase() + item.slice(1))))) : null,
          h("div", { className: "login-privacy" }, "Secure access for the NNCT campus community."))));
  }

  function MetricCard({ metric, index }) {
    return h("article", { className: "metric-card fade-up", style: { animationDelay: `${index * 65}ms` } },
      h("div", { className: "metric-top" },
        h("span", null, metric.label),
        h("span", { className: `metric-icon ${metric.tone}` }, h(Icon, { name: metric.icon, size: 16 }))),
      h("div", { className: "metric-value" }, metric.value),
      h("div", { className: "metric-change" }, metric.change));
  }

  function PanelHeading({ title, subtitle, action }) {
    return h("div", { className: "panel-heading" },
      h("div", null, h("h3", null, title), subtitle ? h("p", null, subtitle) : null),
      action || null);
  }

  function ActivityPanel({ activities }) {
    return h("section", { className: "panel fade-up" },
      h(PanelHeading, { title: "Recent activity", subtitle: "A little progress, every day." }),
      h("div", { className: "activity-list" }, activities.map((item) =>
        h("div", { className: "activity-item", key: item.name },
          h("div", { className: `activity-avatar ${item.tone}` }, item.initials),
          h("div", { className: "activity-info" },
            h("div", { className: "activity-name" }, item.name),
            h("div", { className: "activity-detail" }, item.detail)),
          h("div", { className: "activity-time" }, item.time)))));
  }

  function AttendancePanel({ values }) {
    const labels = ["M", "T", "W", "T", "F", "S", "S", "M", "T", "W", "T", "F"];
    return h("section", { className: "panel fade-up" },
      h(PanelHeading, {
        title: "Attendance overview",
        subtitle: "Campus-wide engagement, week by week.",
        action: h("button", { className: "select-link", type: "button" }, "This semester"),
      }),
      h("div", { className: "chart", "aria-label": "Weekly attendance chart" },
        values.map((value, index) =>
          h("div", { className: "chart-column", key: index, title: `${value}% attendance` },
            h("div", { className: "chart-bar", style: { height: `${value}%`, animationDelay: `${index * 35}ms` } }),
            h("span", { className: "chart-label" }, labels[index])))),
      h("div", { className: "chart-foot" }, h("span", { className: "legend-dot" }), "Attendance rate"));
  }

  function SchedulePanel({ schedule }) {
    return h("section", { className: "panel fade-up" },
      h(PanelHeading, {
        title: "Today's schedule",
        subtitle: "A good day to make it count.",
        action: h("button", { className: "select-link", type: "button" }, "View all"),
      }),
      h("div", { className: "schedule-list" }, schedule.map((item) =>
        h("div", { className: "schedule-item", key: item.time },
          h("div", { className: `schedule-accent ${item.tone}` }),
          h("div", { className: "schedule-copy" },
            h("div", { className: "schedule-course" }, item.course),
            h("div", { className: "schedule-room" }, item.room)),
          h("div", { className: "schedule-time" }, item.time)))));
  }

  function StudentRow({ student, canEdit, canDelete, onSave, onDelete }) {
    const [marks, setMarks] = React.useState(student.marks);
    const [attendance, setAttendance] = React.useState(student.attendance);
    React.useEffect(() => {
      setMarks(student.marks);
      setAttendance(student.attendance);
    }, [student.marks, student.attendance]);
    return h("tr", null,
      h("td", null, h("div", { className: "person-cell" },
        h("div", { className: "person-avatar" }, initials(student.name)),
        h("div", null,
          h("div", { className: "person-name" }, student.name),
          h("div", { className: "person-sub" }, student.student_id)))),
      h("td", null, student.program),
      h("td", null, student.year),
      h("td", null, canEdit
        ? h("input", { className: "record-input", type: "number", min: 0, max: 100, step: 1, required: true, value: attendance, "aria-label": `${student.name} attendance`, onChange: (event) => setAttendance(event.target.value) })
        : `${student.attendance}%`),
      h("td", null, canEdit
        ? h("input", { className: "record-input", type: "number", min: 0, max: 100, step: 1, required: true, value: marks, "aria-label": `${student.name} marks`, onChange: (event) => setMarks(event.target.value) })
        : `${student.marks}%`),
      h("td", null, h("span", { className: `status ${student.status === "Review" ? "review" : ""}` }, student.status)),
      canEdit || canDelete ? h("td", null,
        h("div", { className: "row-actions" },
          canEdit ? h("button", { className: "small-action", type: "button", onClick: () => onSave(student.id, { marks: Number(marks), attendance: Number(attendance) }) }, "Save") : null,
          canDelete ? h("button", { className: "small-action danger-action", type: "button", onClick: () => onDelete(student) }, "Delete") : null)) : null);
  }

  function StudentTable({ rows, search = "", canEdit = false, canDelete = false, onSave, onDelete }) {
    const matching = rows.filter((row) => `${row.name} ${row.student_id} ${row.program}`.toLowerCase().includes(search.toLowerCase()));
    return h("div", { className: "table-wrap" },
      h("table", { className: "data-table" },
        h("thead", null, h("tr", null,
          h("th", null, "STUDENT"),
          h("th", null, "PROGRAM"),
          h("th", null, "YEAR"),
          h("th", null, "ATTENDANCE"),
          h("th", null, "MARKS"),
          h("th", null, "STATUS"),
          canEdit || canDelete ? h("th", null, "ACTIONS") : null)),
        h("tbody", null, matching.length ? matching.map((student) =>
          h(StudentRow, { student, canEdit, canDelete, onSave, onDelete, key: student.id })
        ) : h("tr", null, h("td", { className: "empty-state", colSpan: canEdit || canDelete ? 7 : 6 }, "No students match your search.")))));
  }

  function StaffTable({ rows, canDelete, onDelete }) {
    return h("div", { className: "table-wrap" },
      h("table", { className: "data-table" },
        h("thead", null,
          h("tr", null,
            h("th", null, "FACULTY MEMBER"),
            h("th", null, "DEPARTMENT"),
            h("th", null, "EMAIL"),
            h("th", null, "STATUS"),
            canDelete ? h("th", null, "ACTIONS") : null)),
        h("tbody", null, rows.map((person) =>
          h("tr", { key: person.email },
            h("td", null, h("div", { className: "person-cell" },
              h("div", { className: "person-avatar" }, initials(person.name)),
              h("div", null, h("div", { className: "person-name" }, person.name), h("div", { className: "person-sub" }, person.title)))),
            h("td", null, person.department),
            h("td", null, person.email),
            h("td", null, h("span", { className: "status" }, person.status)),
            canDelete
              ? h("td", null,
                h("button", {
                  className: "small-action danger-action",
                  type: "button",
                  onClick: () => onDelete(person),
                }, "Delete"))
              : null)))));
  }

  function AssignmentsPanel({ assignments }) {
    return h("section", { className: "panel assignment-panel fade-up" },
      h(PanelHeading, { title: "Assigned work", subtitle: "Clear priorities, thoughtful follow-through." }),
      assignments.length ? h("div", { className: "assignment-list" }, assignments.map((assignment) =>
        h("article", { className: "assignment-item", key: assignment.id },
          h("div", { className: "assignment-mark" }, h(Icon, { name: "briefcase", size: 15 })),
          h("div", { className: "assignment-copy" },
            h("div", { className: "assignment-title" }, assignment.title),
            h("div", { className: "assignment-description" }, assignment.description || "No additional instructions."),
            h("div", { className: "assignment-owner" }, `Assigned to ${assignment.staff_name}`)),
          assignment.due_date ? h("span", { className: "assignment-due" }, `Due ${assignment.due_date}`) : null))) :
        h("p", { className: "assignment-empty" }, "No work has been assigned yet."));
  }

  function ManagementDialog({ mode, staff, onClose, onSubmit }) {
    const isStudent = mode === "student";
    const isStaff = mode === "staff";
    const fields = isStudent
      ? [["name", "Student name", "text"], ["student_id", "Student ID", "text"], ["email", "Email address", "email"], ["program", "Program", "text"], ["year", "Year", "text"], ["password", "Temporary password", "password"]]
      : [["name", "Staff name", "text"], ["email", "Email address", "email"], ["title", "Job title", "text"], ["department", "Department", "text"], ["password", "Temporary password", "password"]];
    function submit(event) {
      event.preventDefault();
      onSubmit(Object.fromEntries(new FormData(event.currentTarget).entries()));
    }
    return h("div", { className: "modal-backdrop", onMouseDown: (event) => { if (event.target === event.currentTarget) onClose(); } },
      h("form", { className: "modal-card", onSubmit: submit, role: "dialog", "aria-modal": true, "aria-labelledby": "modal-title" },
        h("button", { className: "modal-close", type: "button", onClick: onClose, "aria-label": "Close" }, "×"),
        h("div", { className: "welcome-eyebrow modal-kicker" }, isStudent ? "Student records" : "Faculty records"),
        h("h2", { id: "modal-title" }, isStudent ? "Add a student" : "Add a staff member"),
        h("p", { className: "login-subtitle" }, "A portal account will be created with this email and temporary password."),
        h("div", { className: "modal-fields" }, fields.map(([name, label, type]) =>
          h("label", { className: "modal-field", key: name },
            h("span", null, label),
            h("input", { name, type, required: true, minLength: type === "password" ? 8 : undefined, autoComplete: type === "password" ? "new-password" : "off" })))),
        h("div", { className: "modal-actions" },
          h("button", { className: "select-link", type: "button", onClick: onClose }, "Cancel"),
          h("button", { className: "primary-action", type: "submit" }, isStaff ? "Create staff account" : "Create student account"))));
  }

  function AssignmentForm({ staff, onSubmit }) {
    function submit(event) {
      event.preventDefault();
      const fields = Object.fromEntries(new FormData(event.currentTarget).entries());
      fields.staff_id = Number(fields.staff_id);
      onSubmit(fields);
      event.currentTarget.reset();
    }
    return h("form", { className: "assignment-form", onSubmit: submit },
      h(PanelHeading, { title: "Assign work", subtitle: "Send a clear task directly to a staff member." }),
      h("div", { className: "assignment-fields" },
        h("label", { className: "modal-field" }, h("span", null, "Staff member"),
          h("select", { name: "staff_id", required: true, defaultValue: "" },
            h("option", { value: "", disabled: true }, "Choose staff"),
            staff.map((member) => h("option", { value: member.id, key: member.id }, member.name)))),
        h("label", { className: "modal-field" }, h("span", null, "Work title"), h("input", { name: "title", required: true, maxLength: 140, placeholder: "e.g. Prepare semester progress report" })),
        h("label", { className: "modal-field" }, h("span", null, "Due date"), h("input", { name: "due_date", type: "date" })),
        h("label", { className: "modal-field field-wide" }, h("span", null, "Instructions"), h("textarea", { name: "description", rows: 3, placeholder: "Add context and expectations…" }))),
      h("button", { className: "primary-action", type: "submit", disabled: staff.length === 0 }, "Assign work"));
  }

  function Dashboard({ user, onLogout }) {
    const [page, setPage] = React.useState(user.allowed_pages[0]);
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [search, setSearch] = React.useState("");
    const [toast, setToast] = React.useState("");
    const [error, setError] = React.useState("");
    const [activeModal, setActiveModal] = React.useState("");
    const [reloadKey, setReloadKey] = React.useState(0);
    const isAdmin = user.role === "admin";
    const canEditRecords = isAdmin || user.role === "staff";
    const title = { overview: "Admin", staff: "Staff", students: "Students" }[page];
    const greetName = user.name.split(" ")[0];
    const isStudent = user.role === "student";

    React.useEffect(() => {
      let active = true;
      setLoading(true);
      setError("");
      api(`/api/dashboard?page=${encodeURIComponent(page)}`)
        .then((result) => { if (active) setData(result); })
        .catch((err) => { if (active) setError(err.message); })
        .finally(() => { if (active) setLoading(false); });
      return () => { active = false; };
    }, [page, reloadKey]);

    React.useEffect(() => {
      if (!toast) return undefined;
      const timer = window.setTimeout(() => setToast(""), 2300);
      return () => window.clearTimeout(timer);
    }, [toast]);

    async function logout() {
      try {
        await api("/api/logout", { method: "POST", body: "{}" });
        onLogout();
      } catch (err) {
        setToast(err.message);
      }
    }

    async function mutate(path, method, body, successMessage) {
      try {
        await api(path, { method, body: JSON.stringify(body) });
        setActiveModal("");
        setToast(successMessage);
        setReloadKey((current) => current + 1);
      } catch (err) {
        setToast(err.message);
      }
    }

    function deleteStudent(student) {
      if (window.confirm(`Delete ${student.name} and their student login? This cannot be undone.`)) {
        mutate(`/api/students/${student.id}`, "DELETE", {}, "Student and login deleted.");
      }
    }

    function deleteStaff(person) {
      if (window.confirm(`Delete ${person.name} and their staff login? Their assigned work will also be removed.`)) {
        mutate(`/api/staff/${person.id}`, "DELETE", {}, "Staff member and login deleted.");
      }
    }

    const nav = user.allowed_pages.map((item) => ({
      id: item,
      label: { overview: "Admin", staff: "Staff", students: "Students" }[item],
      icon: { overview: "overview", staff: "briefcase", students: "users" }[item],
    }));

    const sidebar = h("aside", { className: "sidebar" },
        h("div", { className: "brand" },
          h("img", { src: "/static/images/logo.svg", alt: "" }),
          h("div", null, h("div", { className: "brand-name" }, "NNCT"), h("div", { className: "brand-caption" }, "Campus, connected"))),
        h("div", { className: "nav-label" }, "Workspace"),
        h("nav", { className: "nav-list", "aria-label": "Main navigation" },
          nav.map((item) => h("button", {
            className: `nav-item ${page === item.id ? "active" : ""}`,
            key: item.id,
            type: "button",
            onClick: () => { setPage(item.id); setSearch(""); },
            "aria-current": page === item.id ? "page" : undefined,
          }, h(Icon, { name: item.icon, size: 17 }), h("span", null, item.label)))),
        h("div", { className: "side-bottom" },
          h("div", { className: "campus-card" },
            h("div", { className: "campus-tag" }, h("i"), "Fall semester 2026"),
            h("p", null, "Make this semester count. Your community is right here with you.")),
          h("div", { className: "side-user" },
            h("div", { className: "avatar" }, initials(user.name)),
            h("div", { className: "user-copy" },
              h("div", { className: "user-name" }, user.name),
              h("div", { className: "user-role" }, user.role)),
            h("button", { className: "logout-button", type: "button", onClick: logout, "aria-label": "Sign out", title: "Sign out" }, h(Icon, { name: "logout", size: 15 })))),
      );
    const contentChildren = [
      h("div", { className: "greeting-row", key: "greeting" },
        h("div", null,
          h("h1", null, isStudent ? "Your learning space" : `${new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 18 ? "Good afternoon" : "Good evening"}, ${greetName}`),
          h("p", { className: "subtitle" }, isStudent ? "See what's happening in your NNCT journey." : "Here's what's happening across your campus today.")),
        h("div", { className: "date-pill" }, h(Icon, { name: "calendar", size: 14 }), todayLabel())),
    ];

    if (page === "overview") {
      contentChildren.push(
        h("section", { className: "welcome-card fade-up", key: "welcome" },
          h("div", { className: "welcome-copy" },
            h("div", { className: "welcome-eyebrow" }, "A new week, full of possibility"),
            h("h2", null, "Every student has a story. Help them thrive."),
            h("p", null, "Your campus is showing up — take a look at the good things happening today.")),
          h("div", { className: "welcome-orb" }, h(Icon, { name: "trend", size: 28 })),
          h("button", { className: "welcome-cta", type: "button", onClick: () => { setPage("students"); setToast("Opening your student community."); } }, "Explore students", h(Icon, { name: "arrow", size: 14 }))),
      );
    }

    if (loading) {
      contentChildren.push(h("div", { className: "boot-screen", style: { minHeight: "45vh" }, key: "loading" },
        h("span", { className: "spinner" }), h("span", null, "Loading your campus…")));
    } else if (error) {
      contentChildren.push(h("div", { className: "panel", role: "alert", key: "error" },
        h("p", { className: "login-error" }, error)));
    } else if (data) {
      contentChildren.push(h("div", { className: `metric-grid ${data.metrics.length < 4 ? "compact" : ""}`, key: "metrics" },
        data.metrics.map((metric, index) => h(MetricCard, { metric, index, key: metric.label }))));

      if (page === "students") {
        contentChildren.push(h("section", { className: "page-table", key: "students" },
          h("div", { className: "panel fade-up" },
            h(PanelHeading, {
              title: isStudent ? "Your student record" : "Student directory",
              subtitle: isStudent ? "Your latest marks and attendance, updated by your staff." : "Review and update marks and attendance for your students.",
              action: h("div", { className: "panel-actions" },
                !isStudent ? h("input", { className: "page-search", type: "search", value: search, placeholder: "Search students…", "aria-label": "Search students", onChange: (event) => setSearch(event.target.value) }) : null,
                isAdmin ? h("button", { className: "primary-action", type: "button", onClick: () => setActiveModal("student") }, "+ Add student") : null),
            }),
            h(StudentTable, {
              rows: data.students,
              search,
              canEdit: canEditRecords && !isStudent,
              canDelete: isAdmin,
              onSave: (id, fields) => mutate(`/api/students/${id}`, "PATCH", fields, "Marks and attendance saved."),
              onDelete: deleteStudent,
            }))));
      } else if (page === "staff") {
        contentChildren.push(h("section", { className: "page-table", key: "staff" },
          h("div", { className: "panel fade-up" },
            h(PanelHeading, {
              title: "Faculty directory",
              subtitle: "Meet the people who make a difference on campus.",
              action: isAdmin ? h("button", { className: "primary-action", type: "button", onClick: () => setActiveModal("staff") }, "+ Add staff") : null,
            }),
            h(StaffTable, { rows: data.staff, canDelete: isAdmin, onDelete: deleteStaff }))));
        if (isAdmin) {
          contentChildren.push(h("section", { className: "panel assignment-panel fade-up", key: "assign-form" },
            h(AssignmentForm, { staff: data.staff, onSubmit: (fields) => mutate("/api/assignments", "POST", fields, "Work assigned to staff.") })));
        }
        contentChildren.push(h(AssignmentsPanel, { assignments: data.assignments || [], key: "assignments" }));
      } else {
        contentChildren.push(h("div", { className: "dashboard-grid", key: "dashboard" },
          h(AttendancePanel, { values: data.attendance }),
          h(ActivityPanel, { activities: data.activities })));
        contentChildren.push(h("div", { className: "lower-grid", key: "lower" },
          h("section", { className: "panel fade-up" },
            h(PanelHeading, {
              title: "Student spotlight",
              subtitle: "A few familiar faces from your community.",
              action: h("button", { className: "select-link", type: "button", onClick: () => setPage("students") }, "View directory"),
            }),
            h(StudentTable, { rows: data.students.slice(0, 3) })),
          h(SchedulePanel, { schedule: data.schedule })));
      }
    }

    if (toast) {
      contentChildren.push(h("div", {
        className: `toast ${toast.includes("permission") || toast.includes("error") || toast.includes("already") || toast.includes("required") ? "error-toast" : ""}`,
        role: "status",
        key: "toast",
      }, toast));
    }

    const mainArea = h("main", { className: "main-area" },
      h("header", { className: "topbar" },
        h("div", { className: "breadcrumb" }, "Workspace  /  ", h("b", null, title)),
        h("div", { className: "top-right" },
          h("span", { className: "today" }, todayLabel()),
          h("button", { className: "icon-button", type: "button", "aria-label": "Notifications", onClick: () => setToast("You're all caught up on campus news.") },
            h(Icon, { name: "bell", size: 16 }), h("span", { className: "notification-dot" })),
          h("div", { className: "top-avatar", title: user.name }, initials(user.name)))),
      h("div", { className: "content" }, contentChildren));

    return h("div", { className: "app-shell" }, sidebar, mainArea,
      activeModal ? h(ManagementDialog, {
        mode: activeModal,
        staff: data ? data.staff : [],
        onClose: () => setActiveModal(""),
        onSubmit: (fields) => mutate(
          activeModal === "student" ? "/api/students" : "/api/staff",
          "POST",
          fields,
          activeModal === "student" ? "Student account created." : "Staff account created.",
        ),
      }) : null);
  }

  function App() {
    const [user, setUser] = React.useState(null);
    const [demoCredentials, setDemoCredentials] = React.useState(null);
    const [ready, setReady] = React.useState(false);
    React.useEffect(() => {
      let active = true;
      api("/api/session")
        .then((result) => {
          if (active) {
            setUser(result.user || null);
            setDemoCredentials(result.demo_credentials || null);
          }
        })
        .catch((err) => { if (active && err.message !== "Please sign in to continue.") console.error(err); })
        .finally(() => { if (active) setReady(true); });
      return () => { active = false; };
    }, []);

    if (!ready) return h("div", { className: "boot-screen" }, h("span", { className: "spinner" }), h("span", null, "Getting your campus ready…"));
    return user
      ? h(Dashboard, { user, onLogout: () => setUser(null) })
      : h(Login, { onLogin: setUser, demoCredentials });
  }

  ReactDOM.createRoot(document.getElementById("root")).render(h(App));
})();
