"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Default data used to seed a fresh database.
SEED_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

DB_PATH = current_dir / "activities.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL CHECK (max_participants >= 0)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(activity_id, user_id),
            FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    activity_count = cur.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if activity_count == 0:
        for name, details in SEED_ACTIVITIES.items():
            cur.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    details["description"],
                    details["schedule"],
                    details["max_participants"],
                ),
            )
            activity_id = cur.lastrowid

            for email in details["participants"]:
                cur.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
                user_id = cur.execute(
                    "SELECT id FROM users WHERE email = ?", (email,)
                ).fetchone()[0]
                cur.execute(
                    "INSERT OR IGNORE INTO enrollments (activity_id, user_id) VALUES (?, ?)",
                    (activity_id, user_id),
                )

    conn.commit()
    conn.close()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    conn = get_connection()
    cur = conn.cursor()

    activity_rows = cur.execute(
        """
        SELECT id, name, description, schedule, max_participants
        FROM activities
        ORDER BY name
        """
    ).fetchall()
    enrollment_rows = cur.execute(
        """
        SELECT a.name AS activity_name, u.email AS email
        FROM enrollments e
        JOIN activities a ON a.id = e.activity_id
        JOIN users u ON u.id = e.user_id
        ORDER BY a.name, u.email
        """
    ).fetchall()

    activities = {
        row["name"]: {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": [],
        }
        for row in activity_rows
    }

    for row in enrollment_rows:
        activities[row["activity_name"]]["participants"].append(row["email"])

    conn.close()
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    conn = get_connection()
    cur = conn.cursor()

    activity = cur.execute(
        "SELECT id FROM activities WHERE name = ?", (activity_name,)
    ).fetchone()
    if activity is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    cur.execute("INSERT OR IGNORE INTO users (email) VALUES (?)", (email,))
    user_id = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]

    try:
        cur.execute(
            "INSERT INTO enrollments (activity_id, user_id) VALUES (?, ?)",
            (activity["id"], user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    conn.close()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    conn = get_connection()
    cur = conn.cursor()

    activity = cur.execute(
        "SELECT id FROM activities WHERE name = ?", (activity_name,)
    ).fetchone()
    if activity is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    user = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    deleted = cur.execute(
        "DELETE FROM enrollments WHERE activity_id = ? AND user_id = ?",
        (activity["id"], user["id"]),
    )
    if deleted.rowcount == 0:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    conn.commit()
    conn.close()
    return {"message": f"Unregistered {email} from {activity_name}"}
