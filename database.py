import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    if not DATABASE_URL:
        print("⚠️  DATABASE_URL not set — DB storage disabled.")
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id                SERIAL PRIMARY KEY,
                        session_id        VARCHAR(255),
                        disease           VARCHAR(255),
                        confidence        FLOAT,
                        plant_common_name VARCHAR(255),
                        plant_species     VARCHAR(255),
                        low_confidence    BOOLEAN DEFAULT FALSE,
                        created_at        TIMESTAMP DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS email_reports (
                        id         SERIAL PRIMARY KEY,
                        email      VARCHAR(255) NOT NULL,
                        disease    VARCHAR(255),
                        session_id VARCHAR(255),
                        created_at TIMESTAMP DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS contact_messages (
                        id         SERIAL PRIMARY KEY,
                        name       VARCHAR(255) NOT NULL,
                        email      VARCHAR(255) NOT NULL,
                        phone      VARCHAR(50),
                        subject    VARCHAR(255),
                        message    TEXT NOT NULL,
                        is_read    BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    );

                    ALTER TABLE contact_messages
                        ADD COLUMN IF NOT EXISTS phone   VARCHAR(50);
                    ALTER TABLE contact_messages
                        ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;
                """)
            conn.commit()
        print("✅ Database initialized.")
    except Exception as e:
        print(f"⚠️  Database init failed: {e}")


# ── Predictions ────────────────────────────────────────────────────────────────

def save_prediction(session_id: str, disease: str, confidence: float,
                    plant_common_name: str = "", plant_species: str = "",
                    low_confidence: bool = False):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO predictions
                       (session_id, disease, confidence, plant_common_name, plant_species, low_confidence)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (session_id, disease, confidence,
                     plant_common_name, plant_species, low_confidence)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to save prediction: {e}")


def get_all_predictions(limit: int = 200):
    if not DATABASE_URL:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, session_id, disease, confidence,
                              plant_common_name, plant_species,
                              low_confidence, created_at
                       FROM predictions
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,)
                )
                rows = cur.fetchall()
        return [
            {
                "id": r[0], "session_id": r[1], "disease": r[2],
                "confidence": r[3], "plant_common_name": r[4],
                "plant_species": r[5], "low_confidence": r[6],
                "created_at": str(r[7]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"⚠️  Failed to fetch predictions: {e}")
        return []


def get_disease_stats():
    """Top diseases by frequency — used by admin dashboard chart."""
    if not DATABASE_URL:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT disease, COUNT(*) as count
                       FROM predictions
                       GROUP BY disease
                       ORDER BY count DESC
                       LIMIT 10"""
                )
                rows = cur.fetchall()
        return [{"disease": r[0], "count": r[1]} for r in rows]
    except Exception as e:
        print(f"⚠️  Failed to fetch disease stats: {e}")
        return []


def get_dashboard_stats():
    """Summary counts for admin dashboard cards."""
    if not DATABASE_URL:
        return {"predictions": 0, "emails": 0, "contacts": 0}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM predictions")
                predictions = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM email_reports")
                emails = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM contact_messages")
                contacts = cur.fetchone()[0]
        return {"predictions": predictions, "emails": emails, "contacts": contacts}
    except Exception as e:
        print(f"⚠️  Failed to fetch dashboard stats: {e}")
        return {"predictions": 0, "emails": 0, "contacts": 0}


# ── Email Reports ──────────────────────────────────────────────────────────────

def save_email(email: str, disease: str, session_id: str):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO email_reports (email, disease, session_id) VALUES (%s, %s, %s)",
                    (email, disease, session_id)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to save email: {e}")


def get_all_emails(limit: int = 200):
    if not DATABASE_URL:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, email, disease, session_id, created_at
                       FROM email_reports
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,)
                )
                rows = cur.fetchall()
        return [
            {"id": r[0], "email": r[1], "disease": r[2],
             "session_id": r[3], "created_at": str(r[4])}
            for r in rows
        ]
    except Exception as e:
        print(f"⚠️  Failed to fetch emails: {e}")
        return []


# ── Contact Messages ───────────────────────────────────────────────────────────

def save_contact(name: str, email: str, phone: str, subject: str, message: str):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO contact_messages
                       (name, email, phone, subject, message)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (name, email, phone, subject, message)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to save contact message: {e}")


def get_all_contacts(limit: int = 200):
    if not DATABASE_URL:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, name, email, phone, subject, message, is_read, created_at
                       FROM contact_messages
                       ORDER BY created_at DESC
                       LIMIT %s""",
                    (limit,)
                )
                rows = cur.fetchall()
        return [
            {
                "id": r[0], "name": r[1], "email": r[2], "phone": r[3],
                "subject": r[4], "message": r[5], "is_read": r[6],
                "created_at": str(r[7]),
            }
            for r in rows
        ]
    except Exception as e:
        print(f"⚠️  Failed to fetch contacts: {e}")
        return []


def mark_contact_read(contact_id: int):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE contact_messages SET is_read = TRUE WHERE id = %s",
                    (contact_id,)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to mark contact read: {e}")


def delete_contact(contact_id: int):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM contact_messages WHERE id = %s", (contact_id,)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to delete contact: {e}")


def delete_prediction(prediction_id: int):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM predictions WHERE id = %s", (prediction_id,)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to delete prediction: {e}")
