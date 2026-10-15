# T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence

> **InnoHack 2.0 — Problem Statement C1:** Deepfake and Edited Media Detector  
> **Tagline:** Detect the Manipulation. Verify the Origin. Alert. Report.

---

## 1. Project Overview

**T.R.A.C.E.** is a media-verification prototype designed to assess whether images (and conditionally videos) may have been manipulated or synthesized. It combines:
1. **AI-based Visual Manipulation Inspection**: Employs configurable vision foundation models (via Azure AI Foundry / Azure OpenAI) to inspect scenes for visual inconsistencies, lighting mismatches, and structural anomalies.
2. **Provenance & Integrity Verification**: Inspects media metadata and C2PA Content Credentials where available.
3. **Evidence Presentation & Explainability**: Separates qualitative visual inspection findings from cryptographic provenance.
4. **T.R.A.C.E. ALERT**: Communicates uncertainty clearly without making unsupported claims of absolute authenticity or guilt.
5. **User-Assisted Reporting**: Generates structured, reviewable evidence summaries for official channels (e.g., National Cyber Crime Reporting Portal).

> [!IMPORTANT]
> **Experimental Nature & Limitations:** The visual-analysis model is an experimental heuristic reasoning component. It does NOT calibrate pixel-level forensic probabilities, nor is it a definitive forensic detector. Absence of detected anomalies is not proof of authenticity; presence of visual artifacts may also arise from compression or optical phenomena.

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
│  Analysis Service   │ (Async Orchestration)
└──────┬────────┬─────┘
       │        │
       ▼        ▼
┌────────────┐ ┌────────────────────┐
│ Azure AI   │ │ Provenance /        │
│ Vision     │ │ Metadata Checks     │
│ Adapter    │ │ (conditional)       │
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
│   ├── requirements.txt      # Python dependencies (lightweight, httpx, Pillow)
│   ├── pyproject.toml        # Build configuration and pytest settings
│   ├── app/
│   │   ├── main.py           # Application entrypoint & CORS middleware
│   │   ├── config.py         # Pydantic Settings & environment loader
│   │   ├── api/              # API router and endpoints
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── health.py   # GET /api/v1/health
│   │   │           └── analyze.py  # POST /api/v1/analyze/image (async non-blocking)
│   │   ├── schemas/          # Pydantic schemas (strictly aligned with API_SPEC.md)
│   │   │   ├── health.py
│   │   │   ├── analysis.py
│   │   │   └── error.py
│   │   ├── adapters/         # Decoupled Model Adapter boundaries
│   │   │   ├── base.py                 # BaseInferenceAdapter (predict / predict_async)
│   │   │   ├── azure_vision_adapter.py # Real Azure AI Foundry vision integration
│   │   │   ├── model_adapter.py        # Adapter factory & fallback
│   │   │   └── exceptions.py           # Sanitized domain exceptions
│   │   ├── provenance/       # Provenance / C2PA adapter boundary
│   │   │   └── provenance_adapter.py
│   │   ├── composer/         # Result composition & T.R.A.C.E. alert logic
│   │   │   └── result_composer.py
│   │   ├── services/         # Async orchestration service
│   │   │   └── analysis_service.py
│   │   └── utils/            # Image validation (Pillow decoding, size checks)
│   │       └── media.py
│   └── tests/                # Automated API test suite
│       ├── conftest.py       # Test fixtures (FastAPI TestClient)
│       ├── test_health.py    # Health check verification
│       ├── test_api_contract.py # Contract validation (400, 415, 422, 503)
│       └── test_azure_vision_adapter.py # Comprehensive Azure vision mock suite (16 tests)
└── frontend/                 # Web Frontend (Vite + React + TypeScript)
    ├── package.json          # Node dependencies and scripts
    ├── tsconfig.json         # TypeScript configuration
    ├── vite.config.ts        # Dev server proxy configuration (/api -> :8000)
    ├── index.html            # Application entrypoint HTML
    └── src/                  # React components & UI logic
```

---

## 4. Azure AI Foundry Vision Model Configuration

The backend supports any vision-capable model deployment hosted on Microsoft Azure AI Foundry or Azure OpenAI (e.g., `gpt-4o`, `gpt-4o-mini`, `Phi-3.5-vision-instruct`, `Llama-3.2-11B-Vision`).

### Required Environment Variables

Set the following variables in your local `backend/.env` (copied from `backend/.env.example`):

| Variable | Description | Example |
|---|---|---|
| `AZURE_AI_ENDPOINT` | The Azure endpoint base URL or full chat completions URL | `https://your-resource.openai.azure.com/` |
| `AZURE_AI_API_KEY` | Your Azure API key | `your-secret-api-key` |
| `AZURE_AI_DEPLOYMENT_NAME` | The deployment name configured in Azure AI Foundry | `gpt-4o` or `gpt-4o-mini` |
| `AZURE_AI_API_VERSION` | REST API version supported by the deployment | `2024-08-01-preview` |
| `AZURE_AI_REQUEST_TIMEOUT_SECONDS` | Network timeout for remote inference (default: 30s) | `30.0` |

> **Privacy & Security Note:** Uploaded images are transmitted directly to your configured Azure deployment over encrypted TLS. Images are never transmitted to unapproved third parties. API keys and sensitive tokens are strictly masked and never logged or reflected in error responses.

---

## 5. Development Environment Setup

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

# Edit .env with your Azure AI Foundry deployment details:
# notepad .env

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

### 2. Testing Image Analysis

#### Via Swagger UI:
1. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
2. Expand `POST /api/v1/analyze/image`.
3. Click **Try it out**, upload a supported image (`.jpg`, `.png`, `.webp`), and click **Execute**.

#### Via PowerShell / curl:
```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/analyze/image" `
  -F "file=@path/to/sample.jpg" `
  -F "include_provenance=false"
```

If the Azure environment variables are not yet configured, the endpoint returns a clean `503 Service Unavailable` (`MODEL_UNAVAILABLE`), preventing any fabricated or mock results.

---

## 6. Automated Testing

The automated test suite runs completely offline without requiring live credentials:

```powershell
# From repository root:
.\backend\.venv\Scripts\pytest -v
```

The test suite covers:
1. Azure request URL, header, and body payload construction.
2. Image encoding, base64 data URI conversion, and dimension optimization.
3. Structured output parsing and normalisation.
4. Response mapping into `AnalysisResponse`, `AIDetectionResult`, and `TraceAlert`.
5. Missing configuration handling (503 `MODEL_UNAVAILABLE`).
6. Authentication failure handling (401/403) with secret redaction.
7. Rate limiting (429) and upstream service errors (500/503).
8. Network timeouts and transport errors.
9. Malformed model response rejection without fake fallbacks.
10. Full contract validation per `API_SPEC.md`.

---

## 7. Implementation Roadmap

- [x] **Phase 1: Project Initialization and Environment Setup**
- [x] **Phase 2: Azure Vision Model Assessment & Plan**
- [x] **Phase 3: Azure Vision Model Integration** (Current Phase)
  - Configurable `AzureVisionAdapter` conforming to `BaseInferenceAdapter`.
  - Non-blocking async inference pipeline in FastAPI.
  - Safe error mapping (401, 403, 404, 429, 500, timeout) without leaking secrets.
  - Comprehensive automated test suite (16 passing tests).
- [ ] **Phase 4: Frontend Upload & Results Dashboard**
  - Interactive upload, preview, and results presentation.
  - Dynamic T.R.A.C.E. ALERT messaging and uncertainty communication.
- [ ] **Phase 5: Provenance and Reporting (Conditional)**
  - C2PA / metadata inspection.
  - User-assisted evidence report generation.
