import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

from dotenv import load_dotenv

# Load .env from the project root (one level up from flask_app/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")
load_dotenv(ENV_PATH)

EMAIL_ADDRESS      = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECIPIENT_EMAIL    = os.getenv("RECIPIENT_EMAIL")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465   # SSL port


# ─────────────────────────────────────────
# BUILD EMAIL CONTENT
# ─────────────────────────────────────────
def build_report_text(stats):
    """
    stats is a dict with keys:
      total_active, expiring_this_month (list), expired_not_revoked (list),
      overdue_review (list), report_date
    """
    lines = []
    lines.append("GRC EXCEPTION MANAGEMENT — MONTHLY AUDIT REPORT")
    lines.append("=" * 50)
    lines.append(f"Report Date: {stats['report_date']}")
    lines.append("")
    lines.append(f"# Active exceptions today: {stats['total_active']}")
    lines.append(f"# Exceptions expiring this month: {len(stats['expiring_this_month'])}")
    lines.append(f"# Exceptions overdue for renewal review: {len(stats['overdue_review'])}")
    lines.append(f"# Expired but NOT revoked (critical): {len(stats['expired_not_revoked'])}")
    lines.append("")

    if stats["expired_not_revoked"]:
        lines.append("-" * 50)
        lines.append("CRITICAL — EXPIRED BUT STILL ACTIVE (revoke immediately):")
        for e in stats["expired_not_revoked"][:10]:
            lines.append(f"  • {e['exception_id']} ({e['type']}) — ended {e['end_date']}, requester: {e['requester']}")
        lines.append("")

    if stats["expiring_this_month"]:
        lines.append("-" * 50)
        lines.append("EXPIRING WITHIN 30 DAYS (schedule renewal/revocation):")
        for e in stats["expiring_this_month"][:10]:
            lines.append(f"  • {e['exception_id']} ({e['type']}) — ends {e['end_date']}, requester: {e['requester']}")
        lines.append("")

    if stats["overdue_review"]:
        lines.append("-" * 50)
        lines.append("STALLED APPROVALS (>30 days pending):")
        for e in stats["overdue_review"][:10]:
            lines.append(f"  • {e['exception_id']} ({e['type']}) — requester: {e['requester']}, approver: {e['approver']}")
        lines.append("")

    lines.append("=" * 50)
    lines.append("This is an automated report from the GRC Exception & Policy")
    lines.append("Waiver Management System. Log in to the dashboard for full details.")

    return "\n".join(lines)


# ─────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────
def send_audit_report_email(stats, recipient=None):
    """
    Sends the audit summary report via Gmail SMTP.
    Returns (success: bool, message: str)
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        return False, "Email credentials not configured. Check your .env file."

    to_addr = recipient or RECIPIENT_EMAIL
    if not to_addr:
        return False, "No recipient email configured."

    body = build_report_text(stats)

    msg = MIMEMultipart()
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_addr
    msg["Subject"] = f"GRC Audit Report — {stats['report_date']}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_addr, msg.as_string())
        return True, f"Report sent successfully to {to_addr}"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed — check EMAIL_ADDRESS / EMAIL_APP_PASSWORD in .env"
    except Exception as e:
        return False, f"Failed to send email: {e}"


# ─────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────
if __name__ == "__main__":
    test_stats = {
        "report_date": date.today().isoformat(),
        "total_active": 345,
        "expiring_this_month": [
            {"exception_id": "EXC-0012", "type": "Admin Access", "end_date": "2026-04-25", "requester": "Jane Smith"}
        ],
        "expired_not_revoked": [
            {"exception_id": "EXC-0045", "type": "Firewall Exception", "end_date": "2026-03-01", "requester": "John Doe"}
        ],
        "overdue_review": [
            {"exception_id": "EXC-0099", "type": "VPN Bypass", "requester": "Amy Lee", "approver": "Mark Patel"}
        ],
    }

    print("Sending test email...")
    success, message = send_audit_report_email(test_stats)
    print(("✅ " if success else "❌ ") + message)