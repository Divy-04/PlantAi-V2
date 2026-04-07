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
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    ALTER TABLE contact_messages
                    ADD COLUMN IF NOT EXISTS phone VARCHAR(50);
                """)
            conn.commit()
        print("✅ Database initialized.")
    except Exception as e:
        print(f"⚠️  Database init failed: {e}")

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

def save_contact(name: str, email: str, phone: str, subject: str, message: str):
    if not DATABASE_URL:
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO contact_messages (name, email, phone, subject, message) VALUES (%s, %s, %s, %s, %s)",
                    (name, email, phone, subject, message)
                )
            conn.commit()
    except Exception as e:
        print(f"⚠️  Failed to save contact message: {e}")
