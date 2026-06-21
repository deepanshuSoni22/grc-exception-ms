import os
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime
from collections import defaultdict
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ADMIN_EMAIL    = os.getenv("RECIPIENT_EMAIL")
TODAY          = date(2026, 4, 15)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "grc.db")


# ── helpers ───────────────────────────────────────────────────────

def get_exceptions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM exceptions").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def send_email(to_addr, subject, body_html):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[Scheduler] WARNING: Email credentials not set — skipping send.")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to_addr
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            s.sendmail(EMAIL_ADDRESS, to_addr, msg.as_string())
        print(f"[Scheduler] Sent '{subject}' to {to_addr}")
    except Exception as e:
        print(f"[Scheduler] ERROR sending to {to_addr}: {e}")


def log_notification(exc_id, notif_type, recipient):
    log_path = os.path.join(BASE_DIR, "notification_log.txt")
    with open(log_path, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {notif_type:40s} | {exc_id:12s} | {recipient}\n")


# ── email templates ───────────────────────────────────────────────

def build_requester_email(exc, situation):
    color    = "#dc2626" if situation == "expired" else "#d97706"
    headline = (
        f"Your exception <b>{exc['exception_id']}</b> has <span style='color:{color}'>EXPIRED</span> and is still active."
        if situation == "expired"
        else f"Your exception <b>{exc['exception_id']}</b> expires in <span style='color:{color}'>{exc.get('days_to_expiry','?')} days</span>."
    )
    action = (
        "Please confirm whether your work is complete so the approver can revoke access, or raise a renewal request if you still need it."
        if situation == "expired"
        else "Please confirm if the work will be done before the deadline, or raise a renewal request."
    )
    return f"""
<div style="font-family:sans-serif;max-width:560px;margin:auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
  <div style="background:#0f172a;padding:20px 24px;">
    <h2 style="color:#fff;margin:0;font-size:16px;">GRC Exception Notice</h2>
  </div>
  <div style="padding:24px;">
    <p style="font-size:14px;color:#374151;">Hi <b>{exc['requester']}</b>,</p>
    <p style="font-size:14px;color:#374151;">{headline}</p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
      <tr style="background:#f8fafc;">
        <th style="padding:8px;text-align:left;border-bottom:2px solid #e2e8f0;">Exception ID</th>
        <th style="padding:8px;text-align:left;border-bottom:2px solid #e2e8f0;">Type</th>
        <th style="padding:8px;text-align:left;border-bottom:2px solid #e2e8f0;">End Date</th>
        <th style="padding:8px;text-align:left;border-bottom:2px solid #e2e8f0;">Risk</th>
      </tr>
      <tr>
        <td style="padding:8px;">{exc['exception_id']}</td>
        <td style="padding:8px;">{exc['type']}</td>
        <td style="padding:8px;color:{color};font-weight:600;">{exc['end_date']}</td>
        <td style="padding:8px;">{exc['risk_level']}</td>
      </tr>
    </table>
    <p style="font-size:13px;color:#374151;">{action}</p>
    <p style="font-size:12px;color:#94a3b8;margin-top:24px;">
      Automated message from GRC Exception Management System.<br>
      Your approver: <b>{exc['approver']}</b> has also been notified.
    </p>
  </div>
</div>"""


def build_approver_email(exceptions_list, situation):
    color    = "#dc2626" if situation == "expired" else "#d97706"
    headline = "expired and still ACTIVE" if situation == "expired" else "expiring within 30 days"
    rows = ""
    for e in exceptions_list:
        note = f"Expired {e.get('days_since_expiry','?')}d ago" if situation == "expired" else f"{e.get('days_to_expiry','?')}d left"
        rows += f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #eee;font-family:monospace;color:#3b82f6;">{e['exception_id']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{e['type']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:{color};font-weight:600;">{note}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{e['end_date']}</td>
        </tr>"""
    return f"""
<div style="font-family:sans-serif;max-width:620px;margin:auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
  <div style="background:#0f172a;padding:20px 24px;">
    <h2 style="color:#fff;margin:0;font-size:16px;">Approver Action Required — GRC</h2>
  </div>
  <div style="padding:24px;">
    <p style="font-size:14px;color:#374151;">
      The following exceptions under your approval are <span style="color:{color};font-weight:700;">{headline}</span>.
      Please renew or revoke each one.
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <tr style="background:#f8fafc;">
        <th style="padding:8px;border-bottom:2px solid #e2e8f0;">ID</th>
        <th style="padding:8px;border-bottom:2px solid #e2e8f0;">Type</th>
        <th style="padding:8px;border-bottom:2px solid #e2e8f0;">Status</th>
        <th style="padding:8px;border-bottom:2px solid #e2e8f0;">End Date</th>
      </tr>
      {rows}
    </table>
    <p style="font-size:12px;color:#94a3b8;margin-top:20px;">Automated alert — GRC Exception Management System.</p>
  </div>
</div>"""


def build_admin_digest(expired, expiring, stalled):
    def rows_html(items, note_key):
        out = ""
        for e in items:
            out += f"""<tr>
              <td style="padding:8px;border-bottom:1px solid #eee;font-family:monospace;color:#3b82f6;">{e['exception_id']}</td>
              <td style="padding:8px;border-bottom:1px solid #eee;">{e['type']}</td>
              <td style="padding:8px;border-bottom:1px solid #eee;font-weight:600;">{e.get(note_key,'')}</td>
              <td style="padding:8px;border-bottom:1px solid #eee;">{e['end_date']}</td>
            </tr>"""
        return out

    def section(title, color, items, note_key):
        if not items:
            return f"<p style='color:#10b981;font-size:13px;'>No {title.lower()}.</p>"
        return f"""
        <h3 style="color:{color};font-size:14px;margin-top:20px;">{title} ({len(items)})</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#f8fafc;">
            <th style="padding:8px;border-bottom:2px solid #e2e8f0;">ID</th>
            <th style="padding:8px;border-bottom:2px solid #e2e8f0;">Type</th>
            <th style="padding:8px;border-bottom:2px solid #e2e8f0;">Note</th>
            <th style="padding:8px;border-bottom:2px solid #e2e8f0;">End Date</th>
          </tr>{rows_html(items, note_key)}
        </table>"""

    return f"""
<div style="font-family:sans-serif;max-width:680px;margin:auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
  <div style="background:#0f172a;padding:20px 24px;">
    <h2 style="color:#fff;margin:0;font-size:16px;">GRC Daily Admin Digest — {TODAY}</h2>
  </div>
  <div style="padding:24px;">
    <div style="display:flex;gap:12px;margin-bottom:20px;">
      <div style="flex:1;text-align:center;padding:14px;background:#fff5f5;border-radius:8px;">
        <div style="font-size:24px;font-weight:800;color:#dc2626;">{len(expired)}</div>
        <div style="font-size:11px;color:#dc2626;">Expired Not Revoked</div>
      </div>
      <div style="flex:1;text-align:center;padding:14px;background:#fffbeb;border-radius:8px;">
        <div style="font-size:24px;font-weight:800;color:#d97706;">{len(expiring)}</div>
        <div style="font-size:11px;color:#d97706;">Expiring in 30 Days</div>
      </div>
      <div style="flex:1;text-align:center;padding:14px;background:#eff6ff;border-radius:8px;">
        <div style="font-size:24px;font-weight:800;color:#3b82f6;">{len(stalled)}</div>
        <div style="font-size:11px;color:#3b82f6;">Stalled Reviews</div>
      </div>
    </div>
    {section("Expired — Not Revoked", "#dc2626", expired, "alert_note")}
    {section("Expiring Within 30 Days", "#d97706", expiring, "alert_note")}
    {section("Stalled Reviews", "#3b82f6", stalled, "alert_note")}
    <p style="font-size:12px;color:#94a3b8;margin-top:24px;">Automated daily digest — GRC Exception Management System.</p>
  </div>
</div>"""


# ── main job ──────────────────────────────────────────────────────

def run_daily_notifications():
    print(f"[Scheduler] Running daily job — {datetime.now()}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    all_exc = [dict(r) for r in conn.execute("SELECT * FROM exceptions").fetchall()]

    today_str = TODAY.isoformat()
    expired_active, expiring_soon, stalled = [], [], []
    notified_ids = []

    for exc in all_exc:
        # Skip anything already notified today — prevents re-flooding on every restart
        if exc.get("last_notified") == today_str:
            continue

        end   = datetime.strptime(exc["end_date"],   "%Y-%m-%d").date()
        start = datetime.strptime(exc["start_date"], "%Y-%m-%d").date()
        days_running      = (TODAY - start).days
        days_to_expiry    = (end - TODAY).days
        days_since_expiry = (TODAY - end).days

        if exc["status"] == "ACTIVE" and end < TODAY:
            exc["days_since_expiry"] = days_since_expiry
            exc["alert_note"] = f"Expired {days_since_expiry}d ago"
            expired_active.append(exc)
            notified_ids.append(exc["exception_id"])
        elif exc["status"] == "ACTIVE" and 0 <= days_to_expiry <= 30:
            exc["days_to_expiry"] = days_to_expiry
            exc["alert_note"] = f"Expires in {days_to_expiry}d"
            expiring_soon.append(exc)
            notified_ids.append(exc["exception_id"])
        elif exc["status"] == "PENDING" and days_running > 30:
            exc["alert_note"] = f"Pending {days_running}d"
            stalled.append(exc)

    if not expired_active and not expiring_soon and not stalled:
        print("[Scheduler] Nothing new to notify — all caught up.")
        conn.close()
        return

   # ── ONE consolidated requester summary email (all requesters, one email) ──
    if expired_active or expiring_soon:
        items = expired_active + expiring_soon
        situation = "expired" if expired_active else "expiring"
        html = build_approver_email(items[:25], situation)  # cap table rows for readability
        subject = f"[ACTION NEEDED] {len(items)} exception(s) across all requesters need attention"
        send_email(ADMIN_EMAIL, subject, html)
        log_notification("BATCH", "REQUESTER_SUMMARY_DIGEST", ADMIN_EMAIL)

    # ── ONE consolidated approver summary email (all approvers, one email) ──
    if expired_active or expiring_soon:
        items = expired_active + expiring_soon
        situation = "expired" if expired_active else "expiring"
        html = build_approver_email(items[:25], situation)
        subject = f"[APPROVER SUMMARY] {len(items)} exception(s) need approver action"
        send_email(ADMIN_EMAIL, subject, html)
        log_notification("BATCH", "APPROVER_SUMMARY_DIGEST", ADMIN_EMAIL)

    # ── Admin digest — always sent once per run ──────────────────────
    html = build_admin_digest(expired_active, expiring_soon, stalled)
    send_email(ADMIN_EMAIL, f"GRC Daily Admin Digest — {TODAY}", html)
    log_notification("SUMMARY", "ADMIN_DAILY_DIGEST", ADMIN_EMAIL)

    # ── Mark everything we just processed as notified today ──────────
    if notified_ids:
        conn.executemany(
            "UPDATE exceptions SET last_notified=? WHERE exception_id=?",
            [(today_str, eid) for eid in notified_ids]
        )
        conn.commit()

    conn.close()
    print(f"[Scheduler] Done. Expired={len(expired_active)}, Expiring={len(expiring_soon)}, Stalled={len(stalled)}")
# ── start scheduler (called from app.py) ─────────────────────────

def start_scheduler():
    from datetime import timedelta
    scheduler = BackgroundScheduler()

    # Daily job — real-world schedule
    scheduler.add_job(
        run_daily_notifications,
        trigger="cron",
        hour=8, minute=0,
        id="daily_grc_notifications",
        replace_existing=True
    )

    # Startup catch-up job — runs once, ~5 seconds after Flask starts.
    # This is what makes it "automatic" in a demo: no waiting for 08:00,
    # no manual button. It uses the same last_notified guard, so it only
    # sends for things not already notified today — safe to restart Flask
    # repeatedly without re-flooding the inbox.
    scheduler.add_job(
        run_daily_notifications,
        trigger="date",
        run_date=datetime.now() + timedelta(seconds=5),
        id="startup_catchup_notifications",
        replace_existing=True
    )

    scheduler.start()
    print("[Scheduler] Started — runs once on startup, then daily at 08:00")
    return scheduler


# ── standalone test ───────────────────────────────────────────────

if __name__ == "__main__":
    print("Running in TEST MODE — sends only 3 sample emails, not one per exception.")

    all_exc = get_exceptions()
    expired_list, expiring_list, stalled_list = [], [], []

    for exc in all_exc:
        end   = datetime.strptime(exc["end_date"],   "%Y-%m-%d").date()
        start = datetime.strptime(exc["start_date"], "%Y-%m-%d").date()
        days_running      = (TODAY - start).days
        days_to_expiry    = (end - TODAY).days
        days_since_expiry = (TODAY - end).days

        if exc["status"] == "ACTIVE" and end < TODAY:
            exc["days_since_expiry"] = days_since_expiry
            exc["alert_note"] = f"Expired {days_since_expiry}d ago"
            expired_list.append(exc)
        elif exc["status"] == "ACTIVE" and 0 <= days_to_expiry <= 30:
            exc["days_to_expiry"] = days_to_expiry
            exc["alert_note"] = f"Expires in {days_to_expiry}d"
            expiring_list.append(exc)
        elif exc["status"] == "PENDING" and days_running > 30:
            exc["alert_note"] = f"Pending {days_running}d"
            stalled_list.append(exc)

    # EMAIL 1 — sample requester alert (just the first expired exception)
    if expired_list:
        sample = expired_list[0]
        html = build_requester_email(sample, "expired")
        send_email(ADMIN_EMAIL, f"[SAMPLE] Requester Alert — {sample['exception_id']} expired", html)
        log_notification(sample["exception_id"], "TEST_REQUESTER_ALERT", sample["requester"])
        print(f"  Email 1 sent: requester alert for {sample['exception_id']}")

    # EMAIL 2 — sample approver digest (first 3 expired, grouped)
    if expired_list:
        sample_batch = expired_list[:3]
        html = build_approver_email(sample_batch, "expired")
        send_email(ADMIN_EMAIL, f"[SAMPLE] Approver Digest — {len(sample_batch)} expired exceptions", html)
        log_notification("BATCH", "TEST_APPROVER_DIGEST", ADMIN_EMAIL)
        print(f"  Email 2 sent: approver digest ({len(sample_batch)} items)")

    # EMAIL 3 — full admin digest (all categories, real numbers)
    html = build_admin_digest(expired_list, expiring_list, stalled_list)
    send_email(ADMIN_EMAIL, f"[SAMPLE] Admin Daily Digest — {TODAY}", html)
    log_notification("SUMMARY", "TEST_ADMIN_DIGEST", ADMIN_EMAIL)
    print(f"  Email 3 sent: admin digest (Expired={len(expired_list)}, Expiring={len(expiring_list)}, Stalled={len(stalled_list)})")

    print("\nDone. Check your inbox for exactly 3 emails.")
    print("Check notification_log.txt to see what the real daily job would send.")


# ── REPLACE the if __name__ == "__main__" block with this fixed version ───────