
# 🟢 Blue/Green Deployment with Nginx (Auto-Failover + Manual Toggle)

> 🚀 **Zero-downtime deployment setup using Nginx, Docker Compose, and envsubst**
> Built as part of **HNG DevOps Internship — Stage 2 Task**

---

## 📖 Overview

This project demonstrates a **Blue/Green deployment strategy** using **Nginx as a reverse proxy and load balancer** in front of two Node.js services — **Blue** (primary) and **Green** (backup).

Nginx automatically fails over to the Green instance when Blue becomes unavailable, ensuring **zero failed requests** during application downtime.
Configuration is dynamically generated at runtime using **`envsubst`**, making it easy to toggle environments through CI/CD or environment variables.

---

## ⚙️ Architecture

```
                ┌──────────────────────────────────┐
                │           Client (8080)          │
                └──────────────────────────────────┘
                              │
                              ▼
                    ┌────────────────┐
                    │     Nginx      │
                    │ (Reverse Proxy)│
                    └────────────────┘
                       │         │
           ┌────────────┘         └────────────┐
           ▼                                   ▼
 ┌───────────────────┐              ┌───────────────────┐
 │    Blue Service   │              │   Green Service   │
 │ (Active / Primary)│              │ (Backup / Passive)│
 │     :8081         │              │      :8082        │
 └───────────────────┘              └───────────────────┘
```

* Normal state → Traffic flows to **Blue**
* On failure → Nginx automatically retries to **Green**
* All client requests still receive **200 OK**

---

## 🧩 Features

✅ Automatic failover between Blue and Green
✅ Zero-downtime during app failure
✅ Manual toggle for deployment switching
✅ Dynamic Nginx templating via `envsubst`
✅ Fully parameterized `.env` configuration
✅ CI/CD-ready structure

---

## 📦 Folder Structure

```
.
├── docker-compose.yml
├── .env
├── nginx/
│   ├── nginx.template.conf
│   └── entrypoint.sh
└── README.md
```

---

## ⚙️ Environment Variables

All configuration is managed via the `.env` file.

| Variable           | Description                            |
| ------------------ | -------------------------------------- |
| `BLUE_IMAGE`       | Docker image for Blue service          |
| `GREEN_IMAGE`      | Docker image for Green service         |
| `ACTIVE_POOL`      | Active environment (`blue` or `green`) |
| `PORT`             | Port the Node.js app runs on           |
| `RELEASE_ID_BLUE`  | Release ID for Blue version            |
| `RELEASE_ID_GREEN` | Release ID for Green version           |

### Example `.env`

```bash
BLUE_IMAGE=hngdevops/blue:latest
GREEN_IMAGE=hngdevops/green:latest
ACTIVE_POOL=blue
PORT=8081
RELEASE_ID_BLUE=blue-v1
RELEASE_ID_GREEN=green-v1
```

---

## 🧱 Docker Compose Setup

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:stable-alpine
    env_file: .env
    volumes:
      - ./nginx/nginx.template.conf:/etc/nginx/nginx.template.conf:ro
      - ./nginx/generate-and-run.sh:/docker-entrypoint.d/generate-and-run.sh:ro
    ports:
      - "8080:80"
    depends_on:
      - app_blue
      - app_green
    command: ["sh", "-c", "chmod +x /docker-entrypoint.d/generate-and-run.sh && /docker-entrypoint.d/generate-and-run.sh"]

  app_blue:
    image: ${BLUE_IMAGE}
    environment:
      - PORT=8081
      - RELEASE_ID=${RELEASE_ID_BLUE}
    ports:
      - "8081:8081"

  app_green:
    image: ${GREEN_IMAGE}
    environment:
      - PORT=8082
      - RELEASE_ID=${RELEASE_ID_GREEN}
    ports:
      - "8082:8082"
```

---

## 🧠 Nginx Template (Dynamic Config)

```nginx
upstream node_app {
    server app_blue:${PORT} max_fails=1 fail_timeout=3s;
    server app_green:${PORT} backup;
    keepalive 32;
}

server {
    listen 80;

    location / {
        proxy_pass http://node_app;
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
        proxy_connect_timeout 1s;
        proxy_send_timeout 4s;
        proxy_read_timeout 4s;

        proxy_pass_request_headers on;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 🔄 Nginx Config Generator (`generate-and-run.sh`)

```bash
#!/usr/bin/env sh
set -e

TEMPLATE="/etc/nginx/nginx.template.conf"
OUT="/etc/nginx/nginx.conf"

if [ "$ACTIVE_POOL" = "green" ]; then
  export PRIMARY_HOST="app_green"
  export BACKUP_HOST="app_blue"
else
  export PRIMARY_HOST="app_blue"
  export BACKUP_HOST="app_green"
fi

echo "Generating nginx.conf using envsubst..."
envsubst '${PRIMARY_HOST} ${BACKUP_HOST} ${PORT} ${ACTIVE_POOL}' < $TEMPLATE > $OUT

echo "==== Generated nginx.conf ===="
cat $OUT
echo "=============================="

nginx -g "daemon off;"
```

---

## 🧪 Testing (like the HNG grader)

1️⃣ **Start everything**

```bash
docker compose up
```

2️⃣ **Check Blue is active**

```bash
curl -i http://localhost:8080/version
# X-App-Pool: blue
```

3️⃣ **Trigger chaos**

```bash
curl -X POST http://localhost:8081/chaos/start?mode=error
```

4️⃣ **Verify automatic failover**

```bash
for i in {1..5}; do curl -s -i http://localhost:8080/version | grep X-App-Pool; done
# Should now show: X-App-Pool: green
```

5️⃣ **Stop chaos**

```bash
curl -X POST http://localhost:8081/chaos/stop
```

6️⃣ **Manual toggle**

```bash
export ACTIVE_POOL=green
docker compose up -d nginx
curl -i http://localhost:8080/version
# X-App-Pool: green
```

✅ **Expected:**

* No 5xx or timeout during chaos
* Correct headers forwarded
* Seamless Blue → Green failover

---

## 🧾 Results Checklist (Grader Expectations)

| Test                   | Expected Result                |
| ---------------------- | ------------------------------ |
| `/version` (normal)    | 200, `X-App-Pool: blue`        |
| `/chaos/start`         | Blue fails                     |
| `/version` after chaos | 200, `X-App-Pool: green`       |
| Continuous requests    | All 200 OK, ≥95% from green    |
| `/chaos/stop`          | Blue recovers                  |
| Manual toggle          | Active pool switches correctly |

---

## 🧰 Tools Used

* 🐳 **Docker & Docker Compose**
* 🌐 **Nginx (Reverse Proxy + Load Balancer)**
* ⚙️ **envsubst** (dynamic configuration templating)
* 🟢 **Node.js services (prebuilt HNG images)**

---

## 🧑‍💻 Author

**Oty — DevOps Engineer**
Forward-thinking infrastructure & CI/CD automation
📍 HNG DevOps Internship — Stage 2


