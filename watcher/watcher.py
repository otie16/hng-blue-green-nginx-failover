import os, time, json, re, requests
from collections import deque

LOG_FILE = "/var/log/nginx/access.log"
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 200))
ERROR_THRESHOLD = float(os.getenv("ERROR_RATE_THRESHOLD", 2.0))
COOLDOWN = int(os.getenv("ALERT_COOLDOWN_SEC", 300))

last_alert_time = 0
last_pool = None
window = deque(maxlen=WINDOW_SIZE)

failover_pattern = re.compile(r"pool=(\w+).*upstream_status=(\d+)")
print("🚀 Log watcher started...")

def send_slack(msg):
    global last_alert_time
    now = time.time()
    if now - last_alert_time < COOLDOWN:
        return
    payload = {"text": msg}
    try:
        requests.post(SLACK_WEBHOOK, json=payload)
        last_alert_time = now
        print(f"✅ Sent alert: {msg}")
    except Exception as e:
        print(f"❌ Slack error: {e}")

with open(LOG_FILE, "r") as f:
    f.seek(0, 2)
    while True:
        line = f.readline()
        if not line:
            time.sleep(1)
            continue

        match = failover_pattern.search(line)
        if not match:
            continue

        pool, status = match.groups()
        window.append(int(status))

        # Detect failover
        global last_pool
        if last_pool and pool != last_pool:
            send_slack(f"⚠️ Failover detected! Pool switched from {last_pool} → {pool}")
        last_pool = pool

        # Detect high error rate
        if len(window) >= WINDOW_SIZE:
            errors = sum(1 for s in window if s >= 500)
            error_rate = (errors / len(window)) * 100
            if error_rate > ERROR_THRESHOLD:
                send_slack(f"🚨 High error rate: {error_rate:.2f}% over last {len(window)} requests.")
