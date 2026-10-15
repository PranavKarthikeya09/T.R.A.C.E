# T.R.A.C.E. — Technical Design Document (TDD)

**Project:** T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence  
**Event:** InnoHack 2.0  
**Problem Statement:** C1 — Deepfake and Edited Media Detector  
**Document status:** Initial technical design; proposed choices must be validated before implementation  
**Related document:** `PRD.md`  
**Primary constraint:** 24-hour hackathon  
**Last updated:** 2026-10-15

---

## 1. Purpose

This document describes the proposed technical design for the T.R.A.C.E. MVP: system boundaries, component responsibilities, processing flows, technology-selection criteria, and implementation constraints.

It is a design proposal, not a statement that the architecture or any feature has already been implemented. Confirmed choices and changes should be recorded as development proceeds.

## 2. Design Goals

- Deliver a working image-analysis flow before attempting optional features.
- Use a real, suitable pretrained manipulation-detection model; do not fabricate outputs.
- Keep AI detection separate from provenance verification.
- Make failures, uncertainty, and unavailable checks visible.
- Keep the architecture small enough to implement and test within the hackathon.
- Avoid unnecessary storage, infrastructure, and dependencies.

## 3. Proposed System Architecture

```text
┌─────────────────────┐
│     Web Frontend    │
│ Upload + Results UI │
└──────────┬──────────┘
           │ HTTP / JSON + multipart upload
           ▼
┌─────────────────────┐
│   Python API Server │
│ Validation + Routing│
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Analysis Service  │
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
        │ Result Composer │
        │ Findings +      │
        │ Limitations     │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ Frontend Results│
        │ + TRACE ALERT   │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ Evidence Report │
        │ (conditional)   │
        └─────────────────┘
```

The first implementation can omit provenance checks and report generation until the image-analysis path is working. A database is not required for the basic local MVP.

## 4. Component Responsibilities

### 4.1 Frontend
Responsibilities:
- Provide an image upload control and display supported file requirements.
- Show loading and processing states.
- Display actual analysis output, status, limitations, and errors.
- Present a T.R.A.C.E. ALERT derived from available findings.
- Avoid implying that a result is definitive proof.

The frontend must not calculate, invent, or override model predictions.

### 4.2 API / Backend
Responsibilities:
- Receive uploads and validate them before analysis.
- Enforce configured file type and size limits.
- Pass supported input to the analysis service.
- Convert internal results into a stable response format.
- Return appropriate HTTP errors when validation or analysis fails.
- Manage temporary files and clean them up where practical.

### 4.3 AI Inference Adapter
Responsibilities:
- Load the selected model and its required preprocessing configuration.
- Prepare the image using the model's documented preprocessing steps.
- Run inference and preserve the actual model output.
- Apply the model's documented label mapping.
- Return a structured result with model identifier and output fields.
- Surface loading and inference failures rather than returning a fabricated fallback.

The adapter should isolate model-specific code so the model can be replaced without rewriting upload handling or the response layer.

### 4.4 Provenance / Metadata Adapter — Conditional
Responsibilities, if implemented:
- Inspect supported metadata or provenance credentials.
- Use compatible tooling for the formats being checked.
- Return explicit statuses such as verified, invalid, not found, inconclusive, or unavailable, as supported by the tool.
- Keep provenance findings separate from AI classification.

Missing credentials must not be mapped to “fake.” Valid credentials must not be mapped to “truthful.”

### 4.5 Result Composer and Alert Logic
Responsibilities:
- Combine outputs without erasing the distinction between detection and provenance.
- Produce an understandable summary of completed checks.
- Explain uncertainty and missing/unavailable evidence.
- Generate a caution message based on actual results.

Do not combine scores from unrelated checks into a single “truth score” unless a defensible, validated method is designed and evaluated. The initial MVP should show separate findings.

### 4.6 Evidence Report Generator — Conditional
Responsibilities, if implemented:
- Build a report from stored-in-memory analysis results and user-supplied context.
- Include only facts and outputs actually available.
- Include limitations and analysis time where available.
- Let the user review the report before downloading or using it.
- Avoid asserting criminality or definitive authenticity.

## 5. Proposed Technology Choices

These are candidates, not confirmed dependencies.

| Layer | Candidate | Rationale / condition |
|---|---|---|
| Language | Python | Suitable ecosystem for model inference and backend processing |
| API framework | FastAPI | Lightweight typed API framework; use if compatible with the chosen environment |
| ASGI server | Uvicorn | Common way to run a FastAPI app locally |
| ML framework | PyTorch | Candidate if required by the selected pretrained model |
| Image handling | Pillow | Often sufficient for loading and validating image data |
| Video handling | OpenCV | Add only if video/frame extraction is implemented |
| Frontend | React with JavaScript or TypeScript | Candidate for a separate interactive web interface |
| Styling | Tailwind CSS or plain CSS | Choose based on speed and existing setup |
| Provenance | Compatible C2PA tooling | Add only after verifying support for the target credential format |
| Database | None initially | Add only if persistent history or saved reports are required |
| Deployment | Local first; hosted platform later | Validate model and runtime compatibility before deployment |

**Selection rule:** Do not install the entire candidate stack by default. Select the smallest compatible set after checking the model's license, preprocessing, runtime, memory needs, and available hardware.

## 6. AI Model Selection and Validation

The model is a critical dependency and has not yet been selected.

Evaluate candidate models against:
1. Supported input type and image dimensions.
2. Manipulation types and datasets represented in training/evaluation.
3. Expected generalization limits and known failure modes.
4. Required preprocessing and label interpretation.
5. Runtime, memory, and hardware requirements.
6. Package and framework compatibility.
7. License and usage restrictions.
8. Availability of reproducible tests or suitable evaluation data.
9. Whether the model returns classification only or supports localization.
10. Whether inference is practical in the hackathon environment.

Before integration is considered complete:
- Load the model in the intended environment.
- Run at least one known test input through the real inference path.
- Verify preprocessing and output interpretation against the model documentation.
- Test invalid input and model-loading failure paths.
- Record observed runtime and any relevant environment constraints.
- Do not advertise accuracy unless it has been measured on a suitable dataset.

A classifier's score must not automatically be described as a calibrated probability that the media is fake. If the model does not support localization, do not present heatmaps or pixel-level boundaries as model output.

## 7. Data Flow

### 7.1 Image Analysis — MVP

1. User selects an image in the frontend.
2. Frontend submits it to the backend using multipart form data.
3. Backend checks file presence, allowed type, size, and whether the file can be decoded.
4. Backend passes the image to the inference adapter.
5. Adapter performs documented preprocessing and runs model inference.
6. Adapter returns the actual output and model metadata.
7. Result composer builds the response, including limitations and an appropriately cautious alert.
8. Frontend renders the response.
9. Temporary upload data is removed when no longer required.

### 7.2 Provenance Checks — Conditional

1. The backend receives the media or its safe temporary representation.
2. A compatible verifier checks supported credentials and/or metadata.
3. The verifier returns a specific status and available details.
4. The UI displays these findings separately from the AI result.

If a check cannot run, its status should be “unavailable” or “inconclusive,” not “invalid.”

### 7.3 Video Analysis — Stretch Goal

If implemented, the backend may use OpenCV or another suitable library to decode a video and sample frames. Each analyzed frame must retain its timestamp or frame index. Frame sampling policy, size/duration limits, and error handling must be defined before video support is exposed. Do not claim whole-video coverage when only sampled frames are analyzed.

## 8. API and Module Boundary

The exact API contract belongs in `API_SPEC.md`. The intended separation is:

- Upload/API layer: HTTP concerns and validation.
- Analysis service: orchestration of available checks.
- Model adapter: model-specific loading, preprocessing, and inference.
- Provenance adapter: credential and metadata verification, if enabled.
- Result composer: normalized result and alert wording.
- Report generator: report construction, if enabled.

Keep model code out of route handlers where practical. This separation makes model testing and later replacement easier without requiring a large service architecture.

## 9. Error Handling

The system should distinguish:
- Invalid or missing upload.
- Unsupported file type.
- File too large.
- Image cannot be decoded.
- Model unavailable or failed to load.
- Inference failed.
- Provenance check unavailable or failed.
- Unexpected server error.

Return a clear client-facing message and an appropriate HTTP status. Do not return a normal successful analysis response when inference did not complete. Avoid exposing stack traces, local filesystem paths, secrets, or sensitive internals to the frontend.

## 10. Privacy and Security

- Enforce upload size and type restrictions on the server, not only in the browser.
- Validate that uploaded data can actually be decoded as the expected media type.
- Use safe temporary-file names and locations.
- Do not expose uploaded files through a public static directory.
- Delete temporary files when processing completes, where practical.
- Avoid logging image bytes or unnecessary personal information.
- Do not retain uploaded media or reports by default beyond the required processing lifecycle.
- Keep dependency installation and deployment configuration minimal and reviewable.

## 11. Testing Strategy

### Unit tests
- Upload validation and file-size limits.
- Model output normalization and label mapping.
- Alert wording for representative result states.
- Provenance status mapping, if implemented.
- Report generation, if implemented.

### Integration tests
- Valid image upload through the actual API.
- End-to-end inference using the configured model.
- Invalid file and inference-failure responses.
- Frontend handling of loading, success, and error states.

### Manual demonstration checks
- Upload a supported image.
- Confirm a real model result is displayed.
- Confirm errors are visible and do not look like valid results.
- Confirm limitations are shown.
- Confirm optional features are clearly absent or unavailable if not implemented.

Testing examples alone do not establish model accuracy. Model quality requires appropriate evaluation data and methodology.

## 12. Development and Delivery Strategy

Recommended sequence:

1. Inspect the current development environment and establish the repository structure.
2. Evaluate and validate a suitable pretrained image detector.
3. Implement the inference adapter and test it independently.
4. Implement the upload API and validation.
5. Connect the API to the real inference pipeline.
6. Build the frontend upload and results flow.
7. Add uncertainty-aware T.R.A.C.E. ALERT messaging.
8. Test the complete local demo.
9. Add provenance checks and report generation only if the MVP is stable.
10. Attempt video support or hosted deployment only if time remains.

At each step, preserve working functionality and verify the result before adding the next component.

## 13. Deployment Strategy

Local execution is the first target. Hosted deployment is optional and should follow a successful local test.

Before choosing a host, verify:
- Model and dependency compatibility.
- Memory and compute availability.
- Startup and inference time.
- File-upload restrictions.
- Runtime persistence and temporary-file behaviour.
- License and hosting constraints.

Do not choose a hosting platform solely because it is familiar if the model cannot run reliably there.

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Candidate model cannot run in the available environment | Test early; keep the model adapter replaceable and simplify scope if necessary |
| Model score is misinterpreted as certainty | Display the actual output with clear caveats and documented label meaning |
| Optional features consume the hackathon window | Finish and test the image MVP before adding them |
| Provenance support is incompatible or unavailable | Mark the check unavailable; do not infer that media is fake |
| Video sampling misses manipulation between frames | State the sampling method and avoid claiming exhaustive analysis |
| Uploaded media is exposed or retained unnecessarily | Validate uploads, restrict access, and clean up temporary files |
| Demo displays fabricated or stale results | Use real inference and surface errors rather than hard-coded fallbacks |

## 15. Open Technical Decisions

The following remain unresolved:
- Pretrained detection model and license.
- Model runtime and preprocessing requirements.
- Final frontend framework and styling approach.
- API request/response details, to be finalized in `API_SPEC.md`.
- Supported image formats and maximum upload size.
- Whether C2PA/provenance verification is feasible.
- Whether report generation fits the remaining time.
- Whether video support is feasible after the image pipeline works.
- Deployment platform, if needed.

Do not treat an open decision as confirmed until it has been evaluated or tested.

---

**Current status:** Proposed technical design only. The selected model, framework choices, endpoints, and optional components must be confirmed during implementation.
