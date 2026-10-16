# T.R.A.C.E. — API Specification

**Project:** T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence  
**Event:** InnoHack 2.0  
**Problem Statement:** C1 — Deepfake and Edited Media Detector  
**Document status:** Initial API contract proposal; validate against the implementation before treating it as final  
**Related documents:** `PRD.md`, `TDD.md`  
**Proposed API prefix:** `/api/v1`  
**Primary constraint:** 24-hour hackathon  
**Last updated:** 2026-10-15

---

## 1. Purpose and Contract Rules

This document defines the proposed HTTP interface between the T.R.A.C.E. frontend and backend. It describes endpoint behaviour, input validation, response schemas, and error handling.

This is a proposed contract, not evidence that the endpoints exist. Update the specification if the selected model or implementation requires a justified change.

### Contract rules

- JSON responses use `Content-Type: application/json`, except file downloads.
- Image uploads use `multipart/form-data`.
- All timestamps use ISO 8601 format with a timezone offset; UTC (`Z`) is preferred.
- Do not return fabricated scores or a successful analysis status when inference fails.
- Keep AI detection results separate from provenance findings.
- A missing provenance credential is not proof of manipulation.
- Model scores must not be called probabilities unless the model output is documented and calibrated as such.
- Error responses should not expose stack traces, secrets, or local filesystem paths.

## 2. Endpoint Summary

| Method | Endpoint | Priority | Purpose |
|---|---|---|---|
| `GET` | `/api/v1/health` | MVP | Check whether the API process is available |
| `GET` | `/api/v1/capabilities` | MVP | List supported check availability without exposing configuration values |
| `POST` | `/api/v1/analyze/image` | MVP | Upload and analyze one image |
| `GET` | `/api/v1/analysis/{analysis_id}` | Optional | Retrieve a result during an in-memory analysis lifecycle, if needed |
| `POST` | `/api/v1/analysis/{analysis_id}/report` | Optional | Generate an evidence report from an analysis |
| `GET` | `/api/v1/reports/{report_id}` | Optional | Download a generated report, if implemented |

The MVP can return the analysis result directly from `POST /analyze/image`; it does not need a separate result-retrieval endpoint or persistent storage. The optional endpoints should only be added if the chosen workflow requires them.

## 3. Health Check

### `GET /api/v1/health`

**Purpose:** Confirm that the API process is responding. This endpoint does not by itself guarantee that the AI model is loaded or that inference will succeed.

**Success — `200 OK`**

```json
{
  "status": "ok",
  "service": "trace-api"
}
```

If model readiness needs to be checked separately, add an explicit readiness field or endpoint only after defining how model loading is managed. Do not report model readiness as true without checking it.

### `GET /api/v1/capabilities`

Returns check identifiers with a status such as `available`, `not_configured`, `disabled`, or `unavailable`. The response contains no credential values. This catalog describes server configuration and implementation readiness; it does not guarantee a provider request will succeed.

## 4. Analyze Image

### `POST /api/v1/analyze/image`

**Purpose:** Analyze one supported image using the configured detection model.

**Request content type:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | Image file to analyze |
| `include_provenance` | Boolean/string form field | No | Request provenance checks if supported; default `false` |
| `selected_checks` | JSON array encoded as a string | No | Explicit check identifiers: `visual_assessment`, `ai_generation`, `deepfake`, `metadata`, `spatial_analysis`, `provenance`; omit to retain legacy execution behavior |

When `selected_checks` is supplied, only the listed checks are requested. The server validates identifiers independently of the frontend. The additive `investigation_scope` response field records `selected_checks` and a `check_statuses` map. Check statuses include `completed`, `failed`, `unavailable`, `not_configured`, `disabled`, and `not_requested`. A selected request with incomplete check outcomes may return analysis `status: "partial"`; requests omitting `selected_checks` retain the legacy response behavior.

### Validation requirements

- Reject a missing file.
- Enforce the configured maximum file size on the server.
- Accept only the image formats explicitly supported by the implementation.
- Verify that the file can be decoded as an image; do not trust the extension alone.
- Reject unsupported media with a clear error.
- Do not expose uploaded files through a public static directory.
- The actual supported formats and size limit must be chosen and documented before implementation.

### Success — `200 OK`

The following is an illustrative response shape. Field values are placeholders for schema illustration only; production responses must contain actual inference output. Do not copy example values into application logic as hard-coded results.

```json
{
  "analysis_id": "an_123456",
  "status": "completed",
  "media": {
    "type": "image",
    "filename": "upload.jpg"
  },
  "ai_detection": {
    "status": "completed",
    "model_id": "selected-model-id",
    "label": "model-output-label",
    "score": null,
    "score_semantics": "documented-by-model",
    "interpretation": "Potential manipulation indicated by the model; this is not definitive proof."
  },
  "provenance": {
    "status": "not_requested",
    "checks": []
  },
  "investigation_scope": {
    "selected_checks": ["metadata", "spatial_analysis"],
    "check_statuses": {
      "visual_assessment": "not_requested",
      "ai_generation": "not_requested",
      "deepfake": "not_requested",
      "metadata": "completed",
      "spatial_analysis": "completed",
      "provenance": "not_requested"
    }
  },
  "trace_alert": {
    "level": "caution",
    "message": "Review the findings and verify the original source before trusting or sharing this media."
  },
  "limitations": [
    "Automated detection can be wrong.",
    "This result does not establish whether the media is definitively genuine or manipulated."
  ],
  "created_at": "2026-10-15T12:00:00Z"
}
```

**Important schema notes:**
- `analysis_id` is an opaque identifier for this result. The MVP may generate it per request without persisting it.
- `score` is nullable because not every model exposes a single comparable score. If supplied, document whether it is a logit, raw score, class probability, or calibrated probability.
- `label` must use the selected model's documented labels or a carefully documented mapping.
- `provenance.status` should be `not_requested` if no check was requested, and `unavailable` if requested but unsupported or unable to run.
- `trace_alert.level` is an application-level summary, not a probability or legal determination.
- `created_at` must be generated at analysis time, not copied from an example.

### Suggested enum values

**Analysis `status`:**
- `completed`
- `partial` — a requested selection finished but one or more selected checks were unavailable or failed
- `failed`

For explicit `selected_checks` requests, preserve successful independent results and use `partial` when one or more selected checks do not complete. Legacy requests retain their established response behavior.

**AI detection `status`:**
- `completed`
- `failed`
- `unavailable`

**Provenance `status`:**
- `not_requested`
- `disabled`
- `verified`
- `invalid`
- `not_found`
- `inconclusive`
- `unavailable`

This implementation currently has no C2PA manifest parser or cryptographic signature verifier. A requested provenance check therefore reports `disabled` when the server toggle is off and `unavailable` when enabled; it must not claim a verified, invalid, or absent manifest.

Only expose states the chosen verifier can meaningfully distinguish. If multiple credential checks are performed, a top-level summary may be accompanied by per-check results.

**Alert `level`:**
- `info`
- `caution`
- `inconclusive`

Alert wording must be derived from actual findings. Avoid presenting a low model score as proof that the image is genuine.

## 5. Error Response Contract

Use a consistent error body.

```json
{
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Please upload a supported image format."
  }
}
```

### Proposed HTTP status mapping

| Status | Error code example | Use |
|---|---|---|
| `400 Bad Request` | `MISSING_FILE`, `INVALID_REQUEST` | Required input is absent or malformed |
| `413 Payload Too Large` | `FILE_TOO_LARGE` | Upload exceeds configured size limit |
| `415 Unsupported Media Type` | `UNSUPPORTED_MEDIA_TYPE` | File format is not supported |
| `422 Unprocessable Content` | `INVALID_IMAGE` | File cannot be decoded as a valid supported image |
| `503 Service Unavailable` | `MODEL_UNAVAILABLE` | Model is not available for inference |
| `500 Internal Server Error` | `INFERENCE_FAILED`, `INTERNAL_ERROR` | Unexpected processing failure |

The backend must not leak internal exception text to the client. Diagnostic details may be logged safely on the server without recording uploaded media contents or sensitive information.

If inference fails, return an error response rather than a normal `200` response containing a fabricated result.

## 6. Optional: Retrieve Analysis

### `GET /api/v1/analysis/{analysis_id}`

Add this endpoint only if the frontend needs to retrieve a result after the initial request or if analysis becomes asynchronous.

**Potential responses:**
- `200 OK` — analysis record exists and is accessible.
- `404 Not Found` — identifier is unknown or the result is no longer retained.

For the initial synchronous MVP, this endpoint can be omitted.

## 7. Optional: Generate an Evidence Report

### `POST /api/v1/analysis/{analysis_id}/report`

**Purpose:** Generate a user-reviewable evidence report from an available analysis.

**Request — optional JSON**

```json
{
  "source_url": "https://example.invalid/media",
  "context": "User-provided context about where the media was encountered."
}
```

The example URL is illustrative and must not be treated as a real source. Validate and safely handle user-provided values.

**Potential success — `201 Created`**

```json
{
  "report_id": "rp_123456",
  "status": "generated",
  "format": "pdf",
  "review_required": true
}
```

The report should contain only available facts, actual model findings, checks that were performed, analysis time, and relevant limitations. User-provided context must be distinguished from system-verified facts.

If report generation is implemented, define whether the report is returned directly or stored temporarily for download. Avoid persistent storage unless required.

## 8. Optional: Download a Report

### `GET /api/v1/reports/{report_id}`

If implemented, return the report as a file with an appropriate content type and a safe download filename. Return `404 Not Found` when the report is unknown or no longer available. Apply access controls appropriate to the deployment; do not expose reports through guessable public paths.

For a simple prototype, generating a report in-memory and returning it directly may be simpler than introducing a report store. Choose one approach and document it before implementation.

## 9. Frontend Integration Behaviour

The frontend should:

1. Disable duplicate submissions while a request is in progress, or otherwise handle repeated requests safely.
2. Show a loading state while the backend analyzes the image.
3. Render the result only when a valid success response is received.
4. Render a clear error message for non-success responses.
5. Keep AI findings and provenance findings visually separate.
6. Show limitations alongside the result rather than hiding them in documentation.
7. Never infer that a failed or unavailable analysis means the media is genuine or fake.
8. Avoid displaying model internals or raw server exception details to end users.

## 10. Versioning and Compatibility

- Prefix application endpoints with `/api/v1`.
- Keep response field names stable once frontend integration begins.
- If a breaking contract change becomes necessary, update this document and the frontend together.
- Do not add fields to imply functionality that has not been implemented.
- Optional endpoints can be omitted from the MVP; the frontend must not assume they exist.

## 11. Minimum API Test Checklist

Before declaring the image endpoint usable, test:

- Health endpoint responds.
- Valid supported image reaches real model inference.
- Missing file is rejected.
- Unsupported file type is rejected.
- Oversized file is rejected.
- Corrupt or undecodable image is rejected.
- Model unavailable or inference failure returns an error, not a fake result.
- Successful response matches the documented schema.
- Provenance fields are omitted or explicitly marked unavailable/not requested when no check runs.
- Alert wording does not overstate the model output.
- Sensitive file contents, stack traces, and local paths are not exposed in client responses.

---

**Current status:** Proposed API contract. Endpoint implementation, supported formats, upload limits, model fields, and optional reporting routes must be confirmed and tested before this document is considered final.
