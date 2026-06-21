
import pandas as pd
from datetime import date
from sklearn.metrics import classification_report, confusion_matrix
 
TODAY = date(2026, 4, 15)
 
# ─────────────────────────────────────────
# STEP 1 — RISK SCORE (0 to 100)
# ─────────────────────────────────────────
 
TYPE_SCORE = {
    "Admin Access":            40,
    "Root Access":             40,
    "Firewall Exception":      30,
    "Encryption Waiver":       35,
    "MFA Bypass":              30,
    "VPN Bypass":              20,
    "Data Retention Waiver":   20,
    "Password Policy Exception": 25,
    "Network Access":          20,
}
 
RISK_LEVEL_SCORE = {
    "LOW":      5,
    "MEDIUM":  15,
    "HIGH":    30,
    "CRITICAL":45,
}
 
def calculate_risk_score(row):
    """
    Multi-factor weighted risk score (0–100).
    Factors:
      1. Exception type        (up to 40 pts)
      2. Risk level label      (up to 45 pts)
      3. Duration / age        (up to 20 pts bonus)
      4. Zombie (expired+active)(20 pts penalty)
      5. Justification quality (-5 if very short)
    """
    score = 0
 
    # Factor 1 — type
    score += TYPE_SCORE.get(row["type"], 20)
 
    # Factor 2 — declared risk level
    score += RISK_LEVEL_SCORE.get(row["risk_level"], 10)
 
    # Factor 3 — how long has it actually been running?
    start = pd.to_datetime(row["start_date"]).date()
    end   = pd.to_datetime(row["end_date"]).date()
    days_running = (TODAY - start).days
 
    if days_running > 365:
        score += 20
    elif days_running > 180:
        score += 15
    elif days_running > 90:
        score += 10
    elif days_running > 30:
        score += 5
 
    # Factor 4 — zombie: expired but ACTIVE
    if end < TODAY and row["status"] == "ACTIVE":
        score += 20
 
    # Factor 5 — justification quality (word count)
    word_count = len(str(row["justification"]).split())
    if word_count < 6:
        score += 5   # suspiciously short justification = higher risk
 
    return min(score, 100)   # cap at 100
 
 
# ─────────────────────────────────────────
# STEP 2 — ANOMALY DETECTION (rules engine)
# ─────────────────────────────────────────
 
def detect_anomaly(row):
    """
    Returns (is_anomaly: bool, anomaly_type: str, severity: str)
    Rules applied in priority order.
    """
    start  = pd.to_datetime(row["start_date"]).date()
    end    = pd.to_datetime(row["end_date"]).date()
    status = row["status"]
    risk   = row["risk_level"]
 
    days_running     = (TODAY - start).days
    days_since_expiry = (TODAY - end).days   # positive = already expired
    days_to_expiry    = (end - TODAY).days   # positive = not yet expired
 
    # Rule 1 — EXPIRED but still ACTIVE (most critical)
    if end < TODAY and status == "ACTIVE":
        return True, "EXPIRED_ACTIVE_EXCEPTION", "CRITICAL"
 
    # Rule 2 — CRITICAL risk level, needs re-review
    if risk == "CRITICAL" and status == "ACTIVE":
        return True, "CRITICAL_RISK_EXCEPTION", "CRITICAL"
 
    # Rule 3 — HIGH risk + active >90 days  ← move this UP
    if risk == "HIGH" and days_running > 90 and status == "ACTIVE":
        return True, "HIGH_RISK_LONG_EXCEPTION", "HIGH"

# Rule 4 — Running >180 days
    if days_running > 180 and status == "ACTIVE":
        return True, "LONG_RUNNING_EXCEPTION", "HIGH"
        
 
    # Rule 5 — PENDING review for >30 days (stalled)
    if status == "PENDING" and days_running > 30:
        return True, "STALLED_REVIEW", "MEDIUM"
 
    return False, "NONE", "NONE"
 
 
# ─────────────────────────────────────────
# STEP 3 — RUN ENGINE ON FULL DATASET
# ─────────────────────────────────────────
 
def run_engine(registry_path, labels_path):
    df = pd.read_csv(registry_path)
    df_labels = pd.read_csv(labels_path)
 
    # Apply risk score
    df["risk_score"] = df.apply(calculate_risk_score, axis=1)
 
    # Apply anomaly detection
    results = df.apply(detect_anomaly, axis=1, result_type="expand")
    results.columns = ["predicted_anomaly", "predicted_type", "predicted_severity"]
    df = pd.concat([df, results], axis=1)
 
    # Merge with ground truth
    df = df.merge(df_labels, on="exception_id", suffixes=("", "_actual"))
 
    return df
 
 
# ─────────────────────────────────────────
# STEP 4 — EVALUATE (F1, precision, recall)
# ─────────────────────────────────────────
 
def evaluate(df):
    print("\n" + "="*55)
    print("   GRC RISK ENGINE — EVALUATION REPORT")
    print("="*55)
 
    # Binary anomaly detection
    y_true = df["is_anomaly"].astype(bool)
    y_pred = df["predicted_anomaly"].astype(bool)
 
    print("\n📊 BINARY ANOMALY DETECTION (Anomaly vs Clean)")
    print("-"*55)
    print(classification_report(y_true, y_pred,
          target_names=["Clean", "Anomaly"]))
 
    # Per anomaly type
    print("\n📋 PER-TYPE DETECTION")
    print("-"*55)
    true_types = df["anomaly_type"]
    pred_types = df["predicted_type"]
    all_types = sorted(set(true_types) | set(pred_types))
    print(classification_report(true_types, pred_types,
          labels=all_types, zero_division=0))
 
    # Risk score summary
    print("\n📈 RISK SCORE SUMMARY")
    print("-"*55)
    print(df.groupby("risk_level")["risk_score"].describe()[
        ["mean","min","max"]].round(1).to_string())
 
    # Confusion matrix
    print("\n🔢 CONFUSION MATRIX (Anomaly detection)")
    print("-"*55)
    cm = confusion_matrix(y_true, y_pred)
    print(f"  True Negative  (Clean correctly ignored): {cm[0][0]}")
    print(f"  False Positive (Clean wrongly flagged)  : {cm[0][1]}")
    print(f"  False Negative (Anomaly missed!)        : {cm[1][0]}")
    print(f"  True Positive  (Anomaly correctly caught): {cm[1][1]}")
 
    print("\n✅ Engine evaluation complete.")
    print("="*55)
 
    return df
 
 
# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
 
if __name__ == "__main__":
    REGISTRY = r"P:\grc_system\sample_data\exception_registry.csv"
    LABELS   = r"P:\grc_system\sample_data\exception_labels.csv"
 
    print("🔄 Loading data...")
    df = run_engine(REGISTRY, LABELS)
 
    print(f"✅ Processed {len(df)} records")
    print(f"   Flagged as anomaly : {df['predicted_anomaly'].sum()}")
    print(f"   Clean records      : {(~df['predicted_anomaly']).sum()}")
 
    df_result = evaluate(df)
 
    # Save results
    output_path = r"P:\grc_system\sample_data\scored_exceptions.csv"
    df_result.to_csv(output_path, index=False)
    print(f"\n💾 Scored data saved → {output_path}")
 