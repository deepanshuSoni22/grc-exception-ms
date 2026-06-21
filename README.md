# GRC Exception & Policy Waiver Management System

A full-stack Governance, Risk & Compliance (GRC) tool that centralizes policy exception tracking, scores risk automatically, detects anomalies, and sends fully automated, time-driven notifications — built with Python (Flask), SQLite, and HTML/CSS/JS.

---

## What This System Does

Enterprises grant policy exceptions daily (admin access, firewall rules, encryption waivers). These exceptions get approved but are often **never revoked** after expiry — creating silent security risks.

This system solves that by:
- Centralizing all exceptions in one dashboard
- Automatically scoring each exception's risk (0–100)
- Detecting 5 types of anomalies using a rules-based engine
- Alerting the right people **automatically, with zero manual triggers** — fires the moment the app starts, and again daily at 08:00
- Generating audit-ready reports with one click
- Requiring authenticated login before any data can be accessed

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript, Bootstrap 5, Chart.js |
| ML Evaluation | scikit-learn (classification_report) |
| Notifications | Python smtplib (Gmail SMTP) |
| Scheduler | APScheduler (auto-fires on startup + daily at 08:00) |
| Auth | Flask session-based login, SHA-256 hashed passwords |
| Export | openpyxl (Excel), Print-to-PDF (browser) |

---

## Project Structure

```
grc_system/
├── sample_data/
│   ├── exception_registry.csv      ← 600 synthetic exceptions (Apr 2025–Apr 2026)
│   ├── exception_labels.csv        ← Ground truth labels for evaluation
│   └── scored_exceptions.csv       ← Registry + risk scores + anomaly predictions
├── engine/
│   └── risk_engine.py              ← Multi-factor risk scoring + anomaly detection
├── flask_app/
│   ├── app.py                      ← Main Flask app (all routes, login-protected)
│   ├── database.py                 ← SQLite setup + CSV loader
│   ├── scheduler.py                ← APScheduler — automatic email notifications
│   ├── email_notifications.py      ← Gmail SMTP email sender (manual "Send Report" button)
│   ├── grc.db                      ← SQLite database (auto-created)
│   ├── notification_log.txt        ← Log of all notifications sent
│   └── templates/
│       ├── base.html               ← Master layout (sidebar, session user, sign out)
│       ├── login.html              ← Login page
│       ├── dashboard.html          ← KPI cards + charts + Top Requesters by Risk
│       ├── exceptions.html         ← Sortable, filterable table + Revoke/Renew actions
│       ├── add_exception.html      ← Log new exception form
│       ├── alerts.html             ← Alert monitor (5 categories)
│       ├── report.html             ← Audit report + email/export buttons
│       ├── evaluation.html         ← Model evaluation (F1, accuracy, confusion matrix)
│       └── notification_log.html   ← In-app view of every automated email sent
├── reset_demo.py                   ← One-command reset to clean 600-record demo state
├── .env                            ← Email credentials (NOT submitted)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### 1. Clone / extract the project
```bash
cd P:\
# extract zip or clone repo into grc_system/
```

### 2. Install dependencies
```bash
cd P:\grc_system
pip install -r requirements.txt
```

### 3. Configure email notifications
Create a file called `.env` in `P:\grc_system\` (use terminal, not Notepad):
```bash
cd P:\grc_system
```
Then run in PowerShell:
```powershell
@"
EMAIL_ADDRESS=your_gmail@gmail.com
EMAIL_APP_PASSWORD=your_16char_app_password
RECIPIENT_EMAIL=your_gmail@gmail.com
"@ | Out-File -FilePath .env -Encoding utf8 -NoNewline
```
> **Note:** Gmail requires a 16-character App Password (not your login password).
> Get one at: myaccount.google.com/apppasswords (2FA must be enabled)

### 4. Run the app
```bash
cd P:\grc_system
py flask_app/app.py
```

### 5. Log in
```
http://127.0.0.1:5000
```
Default credentials (seeded automatically the first time the app runs):
- **Username:** `admin`
- **Password:** `admin123`

> All routes are session-protected — visiting any page without logging in redirects straight to `/login`.

### 6. Reset to a clean demo state (recommended before any live demo)
```bash
cd P:\grc_system
py reset_demo.py
```
This wipes the database, re-scores all 600 records from scratch, and clears any test exceptions, revokes/renewals, or notification history you generated while building/testing — so judges see a clean, deterministic dataset.

---

## Features Walkthrough

### Login
- Username/password form, session-based authentication
- Every page (dashboard, registry, alerts, report, evaluation, etc.) is protected — unauthenticated access redirects to `/login`
- Sign Out link in the sidebar footer, showing the currently logged-in user

### Dashboard
- 8 KPI cards: total, active, expiring, expired-not-revoked, critical, high, pending, revoked
- Risk level donut chart + exception type bar chart
- Top 5 high-risk exceptions + recent anomalies detected
- **Top Requesters by Accumulated Risk** — surfaces people holding multiple active exceptions, since 5 medium-risk exceptions on one person is a bigger exposure than 1

### Exception Registry (`/exceptions`)
- All 600+ exceptions in a sortable, filterable table
- Color-coded rows: 🟢 Active · 🟡 Expiring Soon · 🔴 Expired · ⚪ Revoked
- Search by ID, requester, or justification text
- Risk score pill (0–100) and **renewal count** on every row
- **Revoke** / **Renew (+90 days)** action buttons — instantly re-scores the record on renewal

### Log Exception (`/add`)
- Web form to add new exceptions in real time
- Instantly scored and anomaly-checked on submission
- Live word counter on justification (short justifications increase risk score)
- Live risk level indicator

### Alert Monitor (`/alerts`)
Five alert categories, each with recommended action:
| Alert | Trigger | Action |
|-------|---------|--------|
| Expired — Not Revoked | Past end date, still ACTIVE | REVOKE IMMEDIATELY |
| Expiring Soon | Within 30 days | RENEW OR REVOKE |
| Long Running | Active > 180 days | SCHEDULE RENEWAL REVIEW |
| Stalled Review | PENDING > 30 days | ESCALATE TO APPROVER |
| Critical Risk | Risk level = CRITICAL | REVIEW WITH CISO |

### Audit Report (`/report`)
- Executive summary with 4 KPI boxes
- Breakdown by exception type with progress bars
- Top 10 high-risk exceptions (numbered, sorted by score)
- Auto-generated recommendations (IMMEDIATE / THIS MONTH / PROCESS / GOVERNANCE)
- Audit readiness score (0–100%)
- One-click Excel export, Print to PDF, and manual "Send Report via Email" button

### Model Evaluation (`/evaluation`)
- Binary classification report (Anomaly vs Clean)
- Confusion matrix (table + bar chart visual)
- Per anomaly type F1 scores
- Critical anomaly catch rate gauge
- Engine performance grade (A/B/C/D)

### Notification Log (`/notification-log`)
- Full audit trail of every automated email the scheduler has sent — type, exception ID, recipient, and timestamp
- Lets judges verify the automation actually ran, even without checking a real inbox

---

## Risk Scoring Engine

Each exception receives a **0–100 composite risk score** based on:

| Factor | Max Points |
|--------|-----------|
| Exception type (Admin/Root = highest) | 40 pts |
| Declared risk level (CRITICAL = highest) | 45 pts |
| Duration (> 365 days running) | 20 pts |
| Zombie status (expired but still ACTIVE) | 20 pts |
| Justification quality (< 6 words) | 5 pts |

Score thresholds: **85–100** = Critical · **65–84** = High · **45–64** = Medium · **0–44** = Low

---

## Anomaly Detection

5 rules applied in priority order:

| Rule | Condition | Severity |
|------|-----------|---------|
| EXPIRED_ACTIVE_EXCEPTION | end_date < today AND status = ACTIVE | CRITICAL |
| CRITICAL_RISK_EXCEPTION | risk_level = CRITICAL AND status = ACTIVE | CRITICAL |
| HIGH_RISK_LONG_EXCEPTION | HIGH risk AND running > 90 days | HIGH |
| LONG_RUNNING_EXCEPTION | Running > 180 days | HIGH |
| STALLED_REVIEW | PENDING > 30 days | MEDIUM |

Evaluated against `exception_labels.csv` ground truth using `sklearn.classification_report`.

---

## Automated Notifications

Notifications are **fully automatic — no manual trigger required**:

- **On Flask startup** — the scheduler fires once, ~5 seconds after the app launches, so a judge starting the app sees live notification activity immediately without waiting until 08:00
- **Daily at 08:00** — the same job re-runs automatically every day thereafter, as a real production system would

**Deduplication:** every exception that gets notified is stamped with a `last_notified` date. The job only acts on exceptions not already notified *today*, so restarting Flask repeatedly during testing or a demo never re-floods the inbox — it only sends for what's genuinely new.

**What gets sent (capped at 3 emails per run, regardless of dataset size):**

| Email | Content | Recipient |
|-------|---------|-----------|
| Requester summary | All exceptions expired/expiring across all requesters, one consolidated email | Requester(s) |
| Approver summary | All exceptions needing approver action, one consolidated email | Approver(s) |
| Admin daily digest | Full overview — expired, expiring, stalled counts and detail tables | Security/Compliance team |

> **Demo note:** all three emails route to `RECIPIENT_EMAIL` in `.env` so you can see every notification type in one inbox during a demo. In a production deployment with real per-person email addresses, these would route to each actual requester/approver/admin individually.

All notifications — automatic and manual — are logged to `flask_app/notification_log.txt` and viewable in-app at `/notification-log`.

---

## Enterprise Integration Recommendations (ITSM & Beyond)

This system is built as a standalone tool, but is designed to slot into an enterprise environment with minimal effort. Below are the recommended integration points for production deployment.

### ITSM Integration (ServiceNow / Jira Service Management)

**Why:** Most enterprises already manage access requests and change tickets in an ITSM tool. Connecting GRC exceptions to those tickets closes the loop — every exception has a traceable ticket, and revocations can trigger automated change requests.

| Integration Point | How |
|---|---|
| **Auto-create ticket on new exception** | POST to ServiceNow REST API (`/api/now/table/sc_request`) or Jira REST API (`/rest/api/3/issue`) when a new exception is logged via `/add` |
| **Sync ticket status → exception status** | Webhook from ITSM: when a ticket is closed/resolved, auto-update exception status to REVOKED in `grc.db` |
| **Attach audit report to ticket** | On report generation, POST the PDF/Excel to the ITSM attachment endpoint so auditors have a single pane of glass |
| **Escalation tickets** | When the scheduler detects an `EXPIRED_ACTIVE_EXCEPTION`, auto-raise a P1 incident ticket in ServiceNow with the exception ID and owner |

**Implementation path (Flask side):**
```python
# In app.py — after inserting a new exception, fire a ticket creation call
import requests

def create_itsm_ticket(exception_id, exc_type, requester, end_date):
    payload = {
        "short_description": f"GRC Exception {exception_id} — {exc_type}",
        "assignment_group": "Security Compliance",
        "description": f"Requester: {requester}\nExpiry: {end_date}\nReview required.",
        "urgency": "2"
    }
    requests.post(
        "https://your-instance.service-now.com/api/now/table/incident",
        json=payload,
        auth=("sn_user", "sn_password")
    )
```

### Email Integration (Beyond Gmail SMTP)

The current implementation uses Gmail SMTP for simplicity and demo purposes. For production:

| Upgrade | Tool | Benefit |
|---|---|---|
| Transactional email | SendGrid / AWS SES | Delivery tracking, bounce handling, templates |
| Per-person routing | Pull requester email from LDAP/AD | Real emails to real owners, not one inbox |
| HTML email templates | Jinja2 → HTML email | Branded, readable alerts in Outlook/Gmail |
| Email acknowledgement | One-click "I've reviewed this" link in email | Creates an audit trail without logging into the app |

### Active Directory / LDAP Integration

Currently, requester and approver names are free-text. In production:
- Pull the employee directory from **Active Directory** (via `ldap3` Python library) to populate requester/approver dropdowns with real names and emails
- On exception submission, auto-populate the requester's manager as the default approver
- Tie revocation to AD group membership removal (e.g. removing a user from the `admin-access` AD group when their exception is revoked)

### SIEM Integration (Splunk / Microsoft Sentinel)

- Forward the `notification_log.txt` entries to a SIEM as structured events
- Create Splunk alerts that fire when `EXPIRED_ACTIVE_EXCEPTION` count exceeds a threshold
- Dashboard panels in Sentinel pulling live exception counts via the Flask `/dashboard` API response

### API-First Extension

The Flask app can be extended with a REST API layer (already partially present via the `/evaluation` and `/alerts` JSON-capable routes) to support:
- Mobile app consumption
- Third-party GRC platform integration (Archer, OneTrust, ServiceNow GRC module)
- Automated compliance reporting pipelines

---

## Framework Alignment

| Framework | Requirement | How This System Addresses It |
|---|---|---|
| **NIST SP 800-53 AC-2** | Account Management — exceptions must not circumvent controls | Every exception is documented, scored, and tracked to revocation |
| **NIST SP 800-53 PL-4** | Rules of Behavior — exceptions must be documented | Justification field required; short justifications increase risk score |
| **GDPR Article 25** | Data Protection by Design — exceptions undermine this | Expired exceptions flagged immediately; automated revocation alerts |
| **CIS Controls 1.1** | Inventory of IT assets including exceptions | 100% of exceptions centralized, searchable, and audit-exportable |

---

## Dataset

- **600 records** spanning April 2025 – April 2026
- **37% anomaly rate** (222 anomalous records)
- 5 temporal cohorts covering the full exception lifecycle
- Anomaly distribution: EXPIRED_ACTIVE (80), LONG_RUNNING (50), HIGH_RISK_LONG (40), STALLED_REVIEW (30), CRITICAL_RISK (22)

---

## Evaluation Results

| Metric | Score |
|--------|-------|
| Overall Accuracy | ~100% |
| Anomaly F1 Score | ~100% |
| Critical Catch Rate | 100% |
| Engine Grade | A |

> Results are visible live in the app at `/evaluation`

---

## Pre-Submission Checklist

- [ ] Run `py reset_demo.py` for a clean 600-record state
- [ ] Confirm login works with `admin` / `admin123`
- [ ] Confirm logging out and visiting `/dashboard` directly redirects to `/login`
- [ ] Start the app and confirm 1–3 notification emails fire automatically within ~10 seconds, with no manual click
- [ ] Restart the app again and confirm it does **not** re-send the same notifications (dedup working)
- [ ] Walk through Dashboard → Registry → Add Exception → Alerts → Audit Report → Evaluation → Notification Log
- [ ] Test Revoke and Renew on a sample row
- [ ] Export to Excel and confirm the file opens cleanly