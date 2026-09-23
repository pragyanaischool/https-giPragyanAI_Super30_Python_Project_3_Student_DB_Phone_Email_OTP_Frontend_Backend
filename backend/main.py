import os
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from backend.config import settings
from backend.database import init_db, get_db
from backend.services.otp_service import OTPService
from backend.services.twilio_service import TwilioService
from backend.services.email_service import EmailService

# Initialize FastAPI Application
app = FastAPI(
    title="Student DB & OTP Verification API",
    description="Backend API for student registration, Twilio SMS/Email verification, and analytics.",
    version="1.0.0"
)

# ---------------------------------------------------------
# CORS Middleware Configuration
# ---------------------------------------------------------
# Allows requests from local environments as well as live production sites (e.g., Netlify)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*"  # In production, replace '*' with your specific Netlify domain URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
otp_service = OTPService(expiry_seconds=settings.OTP_EXPIRY_SECONDS)
twilio_service = TwilioService()
email_service = EmailService()


# ---------------------------------------------------------
# Lifespan / Startup Event
# ---------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """Ensure database tables and indexes exist on app start."""
    init_db()


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------
class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    department: str = Field(..., min_length=2, max_length=100)
    semester: int = Field(..., ge=1, le=8)


class VerifyOTPRequest(BaseModel):
    identifier: str = Field(..., description="Phone number or email address to verify")
    otp: str = Field(..., min_length=4, max_length=10)
    type: str = Field(..., regex="^(phone|email)$", description="Type must be either 'phone' or 'email'")


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint for Render monitoring."""
    return {"status": "healthy", "service": "student-db-api"}


@app.post("/api/students/register", status_code=status.HTTP_201_CREATED, tags=["Students"])
def register_student(student: StudentCreate):
    """Register a new student and dispatch SMS and Email OTPs."""
    phone_clean = student.phone.strip()
    email_clean = student.email.strip().lower()

    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check uniqueness for email or phone
        cursor.execute(
            "SELECT id FROM students WHERE email = ? OR phone = ?",
            (email_clean, phone_clean)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A student with this email or phone number is already registered."
            )

        # Insert new record
        cursor.execute("""
            INSERT INTO students (name, email, phone, department, semester)
            VALUES (?, ?, ?, ?, ?)
        """, (student.name.strip(), email_clean, phone_clean, student.department.strip(), student.semester))
        conn.commit()

    # Generate and record verification OTPs
    phone_otp = otp_service.generate_otp(phone_clean)
    email_otp = otp_service.generate_otp(email_clean)

    # Dispatch alerts via Twilio and SMTP
    sms_sent = twilio_service.send_sms(
        to_phone=phone_clean,
        message=f"Your verification code is: {phone_otp}. Valid for 5 minutes."
    )
    
    mail_sent = email_service.send_email(
        to_email=email_clean,
        subject="Student Portal Verification Code",
        content=f"Hello {student.name},\n\nYour portal OTP is: {email_otp}\n\nValid for 5 minutes."
    )

    return {
        "message": "Registration successful. OTPs dispatched to both phone and email.",
        "phone": phone_clean,
        "email": email_clean,
        "sms_dispatched": sms_sent,
        "email_dispatched": mail_sent
    }


@app.post("/api/students/verify-otp", tags=["Students"])
def verify_student_otp(payload: VerifyOTPRequest):
    """Verify submitted OTP and update student verification flags."""
    identifier = payload.identifier.strip()
    if payload.type == "email":
        identifier = identifier.lower()

    # Constant-time comparison validation
    is_valid = otp_service.verify_otp(identifier, payload.otp.strip())
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )

    # Determine table columns based on verification type
    target_col = "phone_verified" if payload.type == "phone" else "email_verified"
    id_col = "phone" if payload.type == "phone" else "email"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE students SET {target_col} = 1 WHERE {id_col} = ?",
            (identifier,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student record matching '{identifier}' was not found."
            )
        conn.commit()

    return {"message": f"{payload.type.capitalize()} verified successfully."}


@app.get("/api/analytics", tags=["Analytics"])
def get_analytics():
    """Retrieve operational KPIs, departmental counts, and verification rates."""
    with get_db() as conn:
        cur = conn.cursor()

        # Aggregate counts
        cur.execute("SELECT COUNT(*) FROM students")
        total_students = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM students WHERE phone_verified = 1 AND email_verified = 1")
        fully_verified = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM students WHERE phone_verified = 1 OR email_verified = 1")
        partially_verified = cur.fetchone()[0]

        # Breakdown by department
        cur.execute("""
            SELECT department, COUNT(*) as count 
            FROM students 
            GROUP BY department 
            ORDER BY count DESC
        """)
        dept_distribution = {row["department"]: row["count"] for row in cur.fetchall()}

        # Verification matrix
        cur.execute("""
            SELECT 
                SUM(CASE WHEN phone_verified = 1 AND email_verified = 1 THEN 1 ELSE 0 END) as both_ok,
                SUM(CASE WHEN phone_verified = 1 AND email_verified = 0 THEN 1 ELSE 0 END) as phone_only,
                SUM(CASE WHEN phone_verified = 0 AND email_verified = 1 THEN 1 ELSE 0 END) as email_only,
                SUM(CASE WHEN phone_verified = 0 AND email_verified = 0 THEN 1 ELSE 0 END) as unverified
            FROM students
        """)
        v_row = cur.fetchone()

        # Registration trends (Last 7 daily aggregates)
        cur.execute("""
            SELECT date(created_at) as reg_date, COUNT(*) as count 
            FROM students 
            GROUP BY date(created_at) 
            ORDER BY reg_date DESC 
            LIMIT 7
        """)
        trend_rows = cur.fetchall()
        trends = [{"date": r["reg_date"], "count": r["count"]} for r in reversed(trend_rows)]

    verification_rate = round((fully_verified / total_students * 100), 1) if total_students > 0 else 0.0

    return {
        "kpis": {
            "total_students": total_students,
            "fully_verified": fully_verified,
            "partially_verified": partially_verified,
            "verification_rate": verification_rate
        },
        "department_distribution": dept_distribution,
        "verification_breakdown": {
            "Fully Verified": v_row["both_ok"] or 0,
            "Phone Only": v_row["phone_only"] or 0,
            "Email Only": v_row["email_only"] or 0,
            "Unverified": v_row["unverified"] or 0
        },
        "registration_trend": trends
    }


@app.get("/api/students", tags=["Students"])
def get_students(
    search: Optional[str] = "",
    department: Optional[str] = "",
    status_filter: Optional[str] = "",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """Retrieve filtered, searched, and paginated student records."""
    offset = (page - 1) * limit
    params = []
    where_clauses = ["1=1"]

    if search:
        search_clean = search.strip()
        where_clauses.append("(name LIKE ? OR email LIKE ? OR phone LIKE ?)")
        term = f"%{search_clean}%"
        params.extend([term, term, term])

    if department:
        where_clauses.append("department = ?")
        params.append(department.strip())

    if status_filter == "verified":
        where_clauses.append("phone_verified = 1 AND email_verified = 1")
    elif status_filter == "pending":
        where_clauses.append("(phone_verified = 0 OR email_verified = 0)")

    where_sql = " AND ".join(where_clauses)

    with get_db() as conn:
        cur = conn.cursor()
        
        # Total matching records count
        cur.execute(f"SELECT COUNT(*) FROM students WHERE {where_sql}", params)
        total_records = cur.fetchone()[0]

        # Paginated query
        cur.execute(f"""
            SELECT id, name, email, phone, department, semester, phone_verified, email_verified, created_at
            FROM students
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (*params, limit, offset))

        students = [dict(r) for r in cur.fetchall()]

    total_pages = (total_records + limit - 1) // limit if total_records > 0 else 1

    return {
        "total": total_records,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "students": students
    }


# ---------------------------------------------------------
# Direct Local Run Helper
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
