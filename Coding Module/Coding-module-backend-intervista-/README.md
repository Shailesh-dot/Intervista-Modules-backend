# 🚀 Headless Coding Assessment Engine

A pure, production-ready headless FastAPI microservice tailored for enterprise-grade remote code execution and role-based architectural assessments. 

Designed seamlessly to act as the "Engine Under the Hood" for larger centralized monolithic envelope systems (like a `.NET` main platform).

---

## ✨ System Architecture

*   **Headless Design**: Contains zero frontend logic. Operates cleanly via REST API.
*   **Decoupled State**: Does not mandate internal JWT or Cookie session managers. Takes simple generic tracking identifiers (like `candidate_id`) natively in request bodies, allowing an external envelope completely absolute control of user auth.
*   **Judge0 Integration**: Evaluates code directly by interfacing with a Judge0 CE Docker cluster internally via highly optimized background asynchronous tasks.

## 🛡️ Production Grade Defenses

This module implements severe safeguards to protect VM compute instances under massive multi-user loads:
1.  **DDoS Throttling (`slowapi`)**: `/submit` and `/run` are hard-capped at **5 executions per minute per user** to strictly block malicious spam loops that would crash a Judge0 node.
2.  **Adaptive CPU Constraints**: Infinite `while True` loops are eradicated. Submissions are intelligently checked against database difficulties. Easy questions timeout cleanly after **1.0s**, limiting wasted Worker threads, whilst Hard logic gates allow up to **3.0s**. 
3.  **Adaptive Edge Routing (`fastapi-cache2`)**: Employs an intelligent fallback router. Heavy reading routes automatically cache in-memory or globally in Redis.

---

## ⚡ The Redis Auto-Fallback System

To ensure seamless local testing while providing extreme scalability in Production, this module actively checks for its cache dependencies natively.

**Operating Locally (Development):**
If you do not have a Redis cache configured, the system smartly suppresses errors and falls entirely back to **In-Memory Caching**. You don't need to change a line of code!

**Scaling for Production:**
When your integration team uploads this cluster, they simply append this line to the production `.env` folder:
```env
REDIS_URL="redis://your-redis-server:6379"
```
The App instantly hot-swaps to **Redis Edge Caching** allowing thousands of concurrent users to load code templates with essentially zero Postgres DB queries being dispatched!

---

## 🛠️ Quickstart (Local Laptop Development)

Make sure you've populated your `.env` securely.

1.  **Activate Virtual Environment:**
    ```bash
    source venv/bin/activate
    ```
2.  **Install Global Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Launch Server Engine:**
    ```bash
    bash run.sh
    # Automatically listens securely on 0.0.0.0:8000
    ```

---

## 🐳 Deployment (DigitalOcean / EC2 Production)

The attached `Dockerfile` installs **Gunicorn** dynamically loading `4 Uvicorn Workers`. It handles massive concurrent traffic beautifully natively. 

### Method 1: Bare Docker Run
```bash
# Build the image locally
docker build -t coding-backend .

# Run the image detached passing your env-file mapping it to 8000
docker run -d -p 8000:8000 --env-file .env coding-backend
```

### Method 2: Docker Compose (Recommended)
We've included a highly optimized `docker-compose.yml`. It spins up this robust backend heavily paired flawlessly with a native **Redis** Container to immediately activate Edge Caching!

```bash
docker compose up -d
```
*(If you are running Judge0 on the exact same VM, you can securely transplant the Judge0 `docker-compose` YAML text right into this file and have the whole system boot via a single command!)*

---

## 🔐 Administrative Security Hooks

All Candidate evaluation routes (`POST /submit/`, `GET /question/{id}`) stay public to allow your `.NET` backend full operational power without managing messy Tokens natively. 

However, any **Question Modifying or Creation** (`POST /admin/question`) strictly demands your securely provisioned Header:
```http
X-Admin-Key: <your_admin_secret_key>
```
