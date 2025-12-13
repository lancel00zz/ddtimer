# DDTimer - APM Lab Timer Application

A Flask-based timer/facilitator application used for Datadog APM hands-on labs. The app demonstrates progressive observability instrumentation through different stages.

## Repository Structure

```
ddtimer/
├── 0-baseline/          # Stage 0: Clean app, no Datadog
├── 1-infra/             # Stage 1: Datadog Agent for infra monitoring only
├── 2-apm/               # Stage 2: Full APM instrumentation (with issues)
├── 3-apm-fixed/         # Stage 3: APM with performance fixes applied
├── docker-compose.apm-lab-*.yml   # Student-facing compose files (use pre-built images)
└── README.md
```

### Stages Explained

| Stage | Description | Datadog Agent | APM | Purpose |
|-------|-------------|---------------|-----|---------|
| `0-baseline` | Clean application | ❌ | ❌ | Starting point, no observability |
| `1-infra` | Infrastructure only | ✅ | ❌ | Shows container/host metrics |
| `2-apm` | Full APM | ✅ | ✅ | Shows traces, logs, metrics with intentional perf issues |
| `3-apm-fixed` | APM + Fixes | ✅ | ✅ | Performance issues resolved |

Each stage folder is **self-contained** with its own:
- `app/` - Flask application code
- `config/` - Configuration files
- `Dockerfile` - Container build instructions
- `docker-compose.yml` - **Development** compose (builds locally, mounts code)
- `requirements.txt` - Python dependencies

---

## Quick Reference

### For Students (Running the Labs)

Students use the root-level compose files which pull **pre-built images** from Docker Hub:

```bash
# Run any stage
docker compose -f docker-compose.apm-lab-0-baseline.yml up -d
docker compose -f docker-compose.apm-lab-1-infra.yml up -d
docker compose -f docker-compose.apm-lab-2-apm.yml up -d
docker compose -f docker-compose.apm-lab-3-apm-fixed.yml up -d
```

> **Note:** Stages 1-3 require `DD_API_KEY` environment variable.

### For Developers (Making Changes)

Use the `docker-compose.yml` **inside each stage folder** for development:

```bash
cd 0-baseline   # or 1-infra, 2-apm, 3-apm-fixed
docker compose up -d
```

This builds the image locally and mounts your code for live reloading.

---

## How to Resume Work & Make Changes

### 1. Identify Which Stage to Modify

Determine which stage(s) need changes. Common scenarios:
- **UI changes**: Usually apply to all stages (start with `0-baseline`)
- **APM fixes**: Typically only affect `3-apm-fixed`
- **New features**: May need to propagate across multiple stages

### 2. Start the Development Environment

```bash
# Navigate to the appropriate stage
cd 2-apm   # example

# Start with local build + code mounting
docker compose up -d

# Watch logs
docker compose logs -f ddtimer
```

The app runs at `http://localhost:5049` with live code reloading.

### 3. Make Your Changes

Edit files in the stage folder:
- **Python routes**: `app/routes.py`
- **Templates**: `app/templates/*.html`
- **Static assets**: `app/static/`
- **Configuration**: `config/golden_standard.json`
- **Dependencies**: `requirements.txt`

Changes to `app/` and `config/` are reflected immediately (mounted volumes).
Changes to `requirements.txt` or `Dockerfile` require rebuilding:

```bash
docker compose up -d --build
```

### 4. Propagate Changes to Other Stages (If Needed)

If the change should apply to multiple stages, copy the modified files:

```bash
# Example: Copy updated routes.py from baseline to all stages
cp 0-baseline/app/routes.py 1-infra/app/routes.py
cp 0-baseline/app/routes.py 2-apm/app/routes.py
cp 0-baseline/app/routes.py 3-apm-fixed/app/routes.py
```

### 5. Test Each Stage

```bash
# Test each stage individually
cd 0-baseline && docker compose up -d && docker compose logs -f
# ... verify, then stop and move to next
docker compose down

cd ../1-infra && docker compose up -d
# ... and so on
```

### 6. Publish Updated Images (Multi-Arch)

Once tested, build and push multi-architecture Docker images to support both Intel (amd64) and Apple Silicon (arm64):

```bash
# Ensure buildx is set up (one-time setup)
docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch

# Build and push multi-arch image for a stage
cd 0-baseline
docker buildx build --platform linux/amd64,linux/arm64 \
  -t lancel00zz/ddtimer:0-baseline \
  --push .

# Repeat for other stages if modified
cd ../2-apm
docker buildx build --platform linux/amd64,linux/arm64 \
  -t lancel00zz/ddtimer:2-apm \
  --push .
```

> **Note:** The `--push` flag builds and pushes in one step. Multi-arch images cannot be loaded locally with `--load`; use the regular `docker build` for local testing.

### 7. Update Student Compose Files (If Needed)

If the image tag or environment variables changed, update the root-level compose files:
- `docker-compose.apm-lab-0-baseline.yml`
- `docker-compose.apm-lab-1-infra.yml`
- `docker-compose.apm-lab-2-apm.yml`
- `docker-compose.apm-lab-3-apm-fixed.yml`

---

## Application Details

### Tech Stack
- **Backend**: Flask 3.1 + SQLAlchemy
- **Database**: PostgreSQL 15
- **Instrumentation**: ddtrace (stages 2+)

### Key Endpoints
| Endpoint | Description |
|----------|-------------|
| `/` | Main timer popup |
| `/settings` | Configuration UI |
| `/edit-config?session=X` | Edit session config |
| `/qr-popup` | QR code display |
| `/done?session=X` | Mark task complete |
| `/ping?session=X` | Get completion count |

### Ports
- **App**: 5049 (external) → 5050 (internal)
- **PostgreSQL**: 5439 (external) → 5432 (internal)

### Database

Tables are auto-created on first request. To manually initialize:

```bash
docker compose exec ddtimer python init_db.py
```

---

## Key Differences Between Stages

### 0-baseline vs 2-apm

| File | Difference |
|------|-----------|
| `requirements.txt` | 2-apm adds `ddtrace>=2.10.0,<3.0` |
| `docker-compose.yml` | 2-apm includes DD_* environment variables |

### Student vs Development Compose Files

| Aspect | Student (`docker-compose.apm-lab-*.yml`) | Dev (`*/docker-compose.yml`) |
|--------|------------------------------------------|------------------------------|
| Location | Root folder | Inside stage folder |
| Image source | Pre-built from Docker Hub | Built locally |
| Code mounting | ❌ | ✅ (`./app`, `./config`) |
| Use case | Running labs | Making changes |

---

## Troubleshooting

### Database connection errors
```bash
# Restart the database
docker compose down -v  # Warning: removes data
docker compose up -d
```

### Changes not reflecting
```bash
# Force rebuild
docker compose up -d --build --force-recreate
```

### Check container logs
```bash
docker compose logs -f ddtimer
docker compose logs -f db
```
