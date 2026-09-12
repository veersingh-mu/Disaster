# FloodPath: Production Deployment & Operations Runbook
**Smart India Hackathon 2026 | Problem Statement 26161**

This document provides complete instructions for deploying the FloodPath system locally using Docker Compose or on cloud infrastructure (Render, Railway, Supabase, Vercel).

---

## 1. System Architecture

```
                       +-------------------------------+
                       |      Vercel / Netlify         |
                       |   React 18 + Vite Frontend    |
                       |       (MapLibre GL)           |
                       +---------------+---------------+
                                       |
                                HTTPS / WSS
                                       |
                                       v
                       +-------------------------------+
                       |       Render / Railway        |
                       |      FastAPI Backend API      |
                       | (Security Headers, Rate Limit)|
                       +-------+---------------+-------+
                               |               |
                    PostGIS SQL Engine     In-Memory Queue / Redis
                               |               |
                               v               v
           +-----------------------+   +-----------------------+
           |       Supabase /      |   |   Background Worker   |
           |     Managed PostGIS   |   | (Froehlich, Routing,  |
           |     PostgreSQL 15+    |   |     AI Surrogate)     |
           +-----------------------+   +-----------------------+
```

---

## 2. Environment Variables Specification

Create a `.env` file in the root directory (or configure via cloud provider dashboard):

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:your_password@db:5432/floodpath
DATABASE_URL_SYNC=postgresql://postgres:your_password@db:5432/floodpath

# Security & Authentication
ENVIRONMENT=production
JWT_SECRET=your_super_secret_high_entropy_production_key_32chars_minimum
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Network & CORS Lockdown
CORS_ALLOWED_ORIGINS=https://floodpath.app,https://your-frontend.vercel.app
RATE_LIMIT_RUNS_PER_MINUTE=10
LOG_LEVEL=INFO

# Frontend Configuration
VITE_API_URL=https://api.floodpath.app
```

---

## 3. Deployment Option 1: Docker Compose (All-in-One)

Recommended for on-premise evaluation, jury testing, and staging environments.

### Prerequisites
- Docker Engine 24.0+
- Docker Compose v2.20+

### Step-by-Step Launch
```bash
# 1. Clone repository
git clone https://github.com/your-org/floodpath.git
cd floodpath

# 2. Copy and configure environment variables
cp .env.example .env

# 3. Build and launch all 4 services (db, backend, worker, frontend)
docker-compose up --build -d

# 4. Apply database migrations & seed historical case study (Rishi Ganga 2021)
docker-compose exec backend python -m alembic upgrade head
docker-compose exec backend python -m backend.app.database.seed

# 5. Access the application:
# Frontend UI: http://localhost:5173
# Backend API & Docs: http://localhost:8000/docs
# Healthcheck: http://localhost:8000/health
```

---

## 4. Deployment Option 2: Cloud Infrastructure

### A. Database (Supabase / Managed PostgreSQL with PostGIS)
1. Create a new project on [Supabase](https://supabase.com).
2. Go to **Database** -> **Extensions** and enable `postgis`.
3. Copy the Connection String (URI format).

### B. Backend API (Render / Railway)
1. Deploy from GitHub repository using the `backend/Dockerfile`.
2. Set Environment Variables:
   - `DATABASE_URL=postgresql+asyncpg://...`
   - `DATABASE_URL_SYNC=postgresql://...`
   - `JWT_SECRET=your-secure-32char-secret`
   - `ENVIRONMENT=production`
   - `CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app`
3. Expose Port `8000`. Health check path: `/health`.

### C. Simulation Worker (Render Background Worker / Railway Service)
1. Deploy as a Background Worker using the `worker/Dockerfile`.
2. Connect to the same `DATABASE_URL` and `DATABASE_URL_SYNC`.
3. Command: `python worker/main.py`.

### D. Frontend Web App (Vercel / Netlify)
1. Import `frontend/` directory in Vercel.
2. Build Settings:
   - Framework Preset: **Vite**
   - Build Command: `npm run build`
   - Output Directory: `dist`
3. Environment Variable:
   - `VITE_API_URL=https://your-backend.onrender.com`

---

## 5. Verification & Smoke Testing

Run the automated test and benchmark suite post-deployment:
```bash
# Run 87 unit, integration, and security tests
python -m pytest backend/tests -v

# Run performance and SLA benchmark harness
python -m worker.benchmark

# Run frontend build verification
cd frontend && npm run lint && npm run build
```

---

## 6. Disaster Operations & Incident Response Runbook

1. **Worker Failure / Crash:**
   The backend marks interrupted runs as `FAILED` with diagnostics. The frontend prompts the operator with the "Edit Configuration" or "Retry Simulation" actions.
2. **DEM Outages:**
   The worker transparently relies on local deterministic DEM cache (`worker/cache/dem/`) or high-relief Himalayan parametric models, preventing simulation aborts during satellite/network blackouts.
3. **Emergency Alert Dispatch:**
   Export OASIS CAP v1.2 XML alerts directly via `/scenarios/{id}/alert/cap-xml` and transmit to SEOC / NDMA dissemination systems.
