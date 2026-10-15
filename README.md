# T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence

> **InnoHack 2.0 — Problem Statement C1:** Deepfake and Edited Media Detector  
> **Tagline:** Detect the Manipulation. Verify the Origin. Alert. Report.

---

## 1. Project Overview

**T.R.A.C.E.** is a media-verification system designed to assess whether images (and conditionally videos) have been manipulated. It combines:
1. **AI-based Manipulation Detection**: Leverages pretrained image-manipulation detection models.
2. **Provenance & Integrity Verification**: Inspects media metadata and C2PA Content Credentials.
3. **Evidence Presentation & Explainability**: Separates statistical AI inferences from cryptographic provenance.
4. **T.R.A.C.E. ALERT**: Communicates uncertainty clearly without making unsupported claims of absolute certainty.
5. **User-Assisted Reporting**: Generates structured, reviewable evidence summaries for official channels (e.g., National Cyber Crime Reporting Portal).

---

## 2. System Architecture

Per the Technical Design Document ([TDD.md](file:///c:/Users/PRANAV%20KARTHIKEYA/OneDrive/Desktop/T.R.A.C.E/TDD.md)), the project strictly decouples interface, API routing, media validation, model inference, provenance checking, and report generation:

```text
┌─────────────────────┐
│    Web Frontend     │ (Vite + React + TypeScript)
│ Upload + Results UI │
└──────────┬──────────┘
           │ HTTP / JSON + multipart upload
           ▼
┌─────────────────────┐
│  FastAPI Backend    │ (Python 3.13 / Uvicorn)
│ Validation & Routing│
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Analysis Service   │
└──────┬────────┬─────┘
       │        │
       ▼        ▼
┌────────────┐ ┌────────────────────┐
│ AI Model   │ │ Provenance /        │
│ Inference  │ │ Metadata Checks     │
│ (MVP)      │ │ (conditional)       │
└─────┬──────┘ └─────────┬──────────┘
      └──────────┬───────┘
                 ▼
        ┌─────────────────┐
        │ Result Composer │ -> Composes alert & uncertainty limitations
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ Frontend Results│ -> Displays real outputs & T.R.A.C.E. ALERT
        └─────────────────┘
```

---

## 3. Repository Structure

```text
T.R.A.C.E/
├── .env.example              # Root environment template
├── .gitignore                # Git exclusions (venv, node_modules, secrets, cache)
├── API_SPEC.md               # API Contract specification (Source of Truth)
├── PRD.md                    # Product Requirements Document
├── TDD.md                    # Technical Design Document
├── README.md                 # Project guide and environment instructions
├── pytest.ini                # Test runner configuration
├── docs/                     # Project documentation assets
│   └── showcase_slide.png    # Architecture and showcase slide
├── backend/                  # FastAPI Backend Service
│   ├── .env.example          # Backend environment variables
│   ├── requirements.txt      # Python dependencies
│   ├── pyproject.toml        # Build configuration and pytest settings
│   ├── app/
│   │   ├── main.py           # Application entrypoint & CORS middleware
│   │   ├── config.py         # Pydantic Settings & environment loader
│   │   ├── api/              # API router and endpoints
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── health.py   # GET /api/v1/health
│   │   │           └── analyze.py  # POST /api/v1/analyze/image
│   │   ├── schemas/          # Pydantic schemas (strictly aligned with API_SPEC.md)
│   │   │   ├── health.py
│   │   │   ├── analysis.py
│   │   │   └── error.py
│   │   ├── adapters/         # Decoupled Model Adapter boundary
│   │   │   ├── base.py
│   │   │   └── model_adapter.py
│   │   ├── provenance/       # Provenance / C2PA adapter boundary
│   │   │   └── provenance_adapter.py
│   │   ├── composer/         # Result composition & T.R.A.C.E. alert logic
│   │   │   └── result_composer.py
│   │   ├── services/         # Orchestration service
│   │   │   └── analysis_service.py
│   │   └── utils/            # Image validation (Pillow decoding, size checks)
│   │       └── media.py
│   └── tests/                # Automated API test suite
│       ├── conftest.py       # Test fixtures (FastAPI TestClient)
│       ├── test_health.py    # Health check verification
│       └── test_api_contract.py # Contract validation (400, 415, 422, 503)
└── frontend/                 # Web Frontend (Vite + React + TypeScript)
    ├── package.json          # Node dependencies and scripts
    ├── tsconfig.json         # TypeScript configuration
    ├── vite.config.ts        # Dev server proxy configuration (/api -> :8000)
    ├── index.html            # Application entrypoint HTML
    └── src/                  # React components & UI logic
```

---

## 4. Development Environment Setup

### Prerequisites

- **Python**: 3.11+ (verified on Python 3.13.14 64-bit)
- **Node.js**: v18+ (verified on Node v22.19.0, npm 10.9.3)
- **Git**: 2.x

### 1. Backend Setup

```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment (if not already done)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create local environment configuration
Copy-Item .env.example .env

# Run automated tests
pytest -v

# Start development API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### 2. Frontend Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build / verify bundle
npm run build

# Start frontend development server
npm run dev
```

The frontend will run at [http://localhost:5173/](http://localhost:5173/) and proxy `/api/*` calls directly to the FastAPI server at `http://127.0.0.1:8000`.

---

## 5. API Contract Compliance

The API strictly satisfies the contracts established in `API_SPEC.md`:

| Method | Endpoint | Status | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | 200 OK | Process health indicator (`{"status": "ok", "service": "trace-api"}`) |
| `POST` | `/api/v1/analyze/image` | 200 / Errors | Multipart image analysis endpoint with rigorous validation |

### Error Codes Implemented:
- `400 Bad Request` (`MISSING_FILE`): File absent or empty
- `413 Payload Too Large` (`FILE_TOO_LARGE`): File exceeds configured maximum size
- `415 Unsupported Media Type` (`UNSUPPORTED_MEDIA_TYPE`): Non-whitelisted extension
- `422 Unprocessable Content` (`INVALID_IMAGE`): Undecodable / corrupt image stream
- `503 Service Unavailable` (`MODEL_UNAVAILABLE`): Returned when detector model is uninitialized (Phase 1 safeguard against fabricated outputs)
- `500 Internal Server Error` (`INTERNAL_ERROR` / `INFERENCE_FAILED`): Sanitized error handling that prevents internal stack traces from leaking to clients

---

## 6. Implementation Phases

- [x] **Phase 1: Project Initialization and Environment Setup** (Current Phase)
  - Environment inspection and runtime verification.
  - Project directory structure established per `TDD.md`.
  - Backend dependencies installed, schemas and API contract established per `API_SPEC.md`.
  - Frontend toolchain scaffolded and verified.
  - Automated test suite verifying contract rules.
- [ ] **Phase 2: AI Model Selection and Inference Pipeline**
  - Evaluate pretrained image manipulation detection model.
  - Implement real inference adapter with documented preprocessing.
  - Validate model outputs against authentic test samples.
- [ ] **Phase 3: Integration and UI Development**
  - Interactive upload, preview, and results presentation.
  - Dynamic T.R.A.C.E. ALERT messaging and uncertainty communication.
- [ ] **Phase 4: Provenance and Reporting (Conditional)**
  - C2PA / metadata inspection.
  - User-assisted evidence report generation.
