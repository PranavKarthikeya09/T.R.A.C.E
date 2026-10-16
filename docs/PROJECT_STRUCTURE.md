# Project Structure

This guide separates the application that runs from tests, research tooling, and local machine state. Keep the existing directories in place; the backend and frontend are connected through the documented API contract.

## Application paths

```text
T.R.A.C.E/
├── backend/
│   ├── app/                    # FastAPI application and runtime code
│   │   ├── main.py             # ASGI entry point: app.main:app
│   │   ├── api/v1/             # Versioned routes and endpoint handlers
│   │   ├── schemas/             # Request and response models
│   │   ├── services/            # Analysis orchestration
│   │   ├── adapters/            # Vision provider integration boundaries
│   │   ├── forensics/           # Local image evidence extraction
│   │   ├── provenance/          # Provenance checks
│   │   ├── composer/            # Response and finding composition
│   │   └── utils/               # Shared media utilities
│   ├── tests/                   # Backend tests and test fixtures
│   ├── evaluation/              # Offline dataset, evaluation, and audit work
│   ├── requirements.txt         # Backend dependency list
│   ├── pyproject.toml           # Python tooling and project settings
│   └── .env.example             # Backend configuration template (no secrets)
├── frontend/
│   ├── src/                     # React application, components, API client, types
│   ├── public/                  # Static public assets
│   ├── package.json             # Frontend scripts and dependencies
│   └── package-lock.json        # npm dependency lockfile
├── docs/                        # Project-level documentation and visuals
├── API_SPEC.md                  # API contract reference
├── PRD.md                       # Product requirements
├── TDD.md                       # Technical design
├── pytest.ini                   # Root test discovery settings
└── README.md                    # Setup, operation, and project overview
```

## Request flow

`frontend/src/services/api.ts` sends requests to the versioned FastAPI routes in `backend/app/api/v1/`. The route validates input and delegates to `backend/app/services/`; provider, forensics, and provenance work stays behind their respective adapter/modules. `backend/app/composer/` builds the response described in `API_SPEC.md`.

Preserve that boundary when changing code: UI changes belong in `frontend/`; endpoint contracts belong in `API_SPEC.md` and the backend schemas/routes; detector implementations belong in their existing backend modules.

## Tests and evaluation

- `backend/tests/` contains automated checks for API behavior and backend modules. Test images here are fixtures, not runtime uploads.
- `backend/evaluation/` contains offline evaluation scripts, manifests, sample datasets, derived variants, and model weights. These support research and validation; they are not loaded by the normal API startup path.
- Root and frontend setup instructions remain in `README.md` and `frontend/README.md` respectively.

## Local-only files

Virtual environments (`backend/.venv*`), `.env` files, `frontend/node_modules/`, build output, and evaluation data/cache/weights are machine-local or generated. The repository `.gitignore` excludes these. Do not move or delete an existing environment or evaluation artifact as part of routine source cleanup; recreate environments only through the documented dependency setup if needed.

## Validation entry points

- Backend API: `backend/app/main.py`, served as `app.main:app` from the `backend/` directory.
- Frontend: `frontend/src/main.tsx`, built and served using scripts in `frontend/package.json`.
- API compatibility: `API_SPEC.md` and backend schema/contract tests.
