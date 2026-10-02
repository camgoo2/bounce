"""
Database Migration Script
Adds email, password_hash, device_token, and created_at columns to User table
"""
import sqlite3
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "events.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔄 Starting database migration...")

    # Check if email column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'email' not in columns:
        print("  Adding email column...")
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

    if 'password_hash' not in columns:
        print("  Adding password_hash column...")
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

    if 'device_token' not in columns:
        print("  Adding device_token column...")
        cursor.execute("ALTER TABLE users ADD COLUMN device_token TEXT")

    if 'created_at' not in columns:
        print("  Adding created_at column...")
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")

    # Update existing users with default values
    cursor.execute("SELECT id, username, email FROM users")
    users = cursor.fetchall()

    default_password = "password123"  # Default password for testing
    password_hash = pwd_context.hash(default_password)

    for user_id, username, email in users:
        if not email:
            # Generate email from username
            email = f"{username}@bounce.test"
            cursor.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
            print(f"  Updated user {username}: email = {email}")

        # Set default password hash if not set
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone()[0]:
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
            print(f"  Updated user {username}: password = {default_password}")

    # Create unique indexes
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        print("  Created unique index on email")
    except:
        pass

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        print("  Created index on username")
    except:
        pass

    conn.commit()
    conn.close()

    print("✅ Migration completed successfully!")
    print(f"\n📝 Note: Existing users have been set with default password: '{default_password}'")
    print("   You can login with username and this password, then change it later.\n")

if __name__ == "__main__":
    migrate()
