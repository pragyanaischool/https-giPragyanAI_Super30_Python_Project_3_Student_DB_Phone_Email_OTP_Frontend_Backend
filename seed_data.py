import sqlite3
import random
import hashlib
from datetime import datetime, timedelta

# Default path matches settings.DATABASE_PATH
DB_PATH = "students.db"

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Pooja", "Vikram", "Sneha", "Rahul", "Ananya",
    "Karan", "Ishita", "Arjun", "Priyanka", "Amit", "Divya", "Siddharth", "Neha",
    "Manish", "Tanvi", "Kunal", "Riya", "Gaurav", "Simran", "Deepak", "Kavya",
    "Nikhil", "Meera", "Varun", "Shruti", "Akash", "Tanya", "Harsh", "Bhavna",
    "Mayank", "Shweta", "Yash", "Kritika", "Abhishek", "Ritika", "Prateek", "Sakshi"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Patel", "Mehta", "Singh", "Reddy", "Nair",
    "Iyer", "Chopra", "Joshi", "Bhatia", "Deshmukh", "Agarwal", "Rao", "Kumar",
    "Mishra", "Pandey", "Saxena", "Choudhury"
]

DEPARTMENTS = [
    "Computer Science",
    "Artificial Intelligence",
    "Information Tech",
    "Data Science",
    "Electronics"
]


def hash_password(password: str) -> str:
    """Returns a SHA-256 hash of the plain-text password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_database(total_students: int = 125) -> None:
    """Seeds admin and student records into SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Ensure required tables exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'superadmin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
            phone_verified INTEGER NOT NULL DEFAULT 0 CHECK (phone_verified IN (0, 1)),
            email_verified INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Reset existing records for a clean run
    cur.execute("DELETE FROM students;")
    cur.execute("DELETE FROM admins;")
    cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'admins');")

    # 3. Seed Default Admin Account
    admin_user = "admin"
    admin_email = "admin@pragyanai.com"
    admin_pass = hash_password("admin123")
    
    cur.execute("""
        INSERT INTO admins (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """, (admin_user, admin_email, admin_pass, "superadmin"))

    # 4. Generate Unique Student Records
    used_emails = set()
    used_phones = set()
    students_batch = []

    now = datetime.now()

    for idx in range(1, total_students + 1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        # Ensure guaranteed unique email
        email_candidate = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 999)}@gmail.com"
        while email_candidate in used_emails:
            email_candidate = f"{first_name.lower()}.{last_name.lower()}{random.randint(1000, 99999)}@gmail.com"
        used_emails.add(email_candidate)

        # Ensure guaranteed unique phone number (E.164 format)
        phone_candidate = f"+91{random.randint(6000000000, 9999999999)}"
        while phone_candidate in used_phones:
            phone_candidate = f"+91{random.randint(6000000000, 9999999999)}"
        used_phones.add(phone_candidate)

        dept = random.choice(DEPARTMENTS)
        semester = random.randint(1, 8)

        # Realistic distribution: ~50% both, ~25% phone only, ~15% email only, ~10% none
        dice = random.random()
        if dice < 0.50:
            phone_verified, email_verified = 1, 1
        elif dice < 0.75:
            phone_verified, email_verified = 1, 0
        elif dice < 0.90:
            phone_verified, email_verified = 0, 1
        else:
            phone_verified, email_verified = 0, 0

        # Spread timestamps over the last 30 days
        days_back = random.randint(0, 30)
        hours_back = random.randint(0, 23)
        minutes_back = random.randint(0, 59)
        created_time = (now - timedelta(days=days_back, hours=hours_back, minutes=minutes_back)).strftime("%Y-%m-%d %H:%M:%S")

        students_batch.append((
            full_name,
            email_candidate,
            phone_candidate,
            dept,
            semester,
            phone_verified,
            email_verified,
            created_time
        ))

    # 5. Bulk Insert
    cur.executemany("""
        INSERT INTO students (
            name, email, phone, department, semester, 
            phone_verified, email_verified, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, students_batch)

    conn.commit()
    conn.close()

    print("==================================================")
    print("Database seeding completed successfully!")
    print(f"Total Admin Records Created : 1 (User: {admin_user} / Pass: admin123)")
    print(f"Total Student Records Created: {total_students}")
    print(f"Target Database File       : {DB_PATH}")
    print("==================================================")


if __name__ == "__main__":
    seed_database(125)
