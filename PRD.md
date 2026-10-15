# T.R.A.C.E. — Product Requirements Document (PRD)

**Project:** T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence  
**Event:** InnoHack 2.0  
**Problem Statement:** C1 — Deepfake and Edited Media Detector  
**Document status:** Initial draft; requirements are proposed until validated during implementation  
**Primary constraint:** 24-hour hackathon  
**Last updated:** 2026-10-15

---

## 1. Product Overview

T.R.A.C.E. is a media-verification prototype intended to help users assess whether images or videos may have been manipulated. It combines AI-based manipulation detection with checks for available media-origin and integrity evidence, then explains the findings and provides user-assisted reporting support when appropriate.

**Tagline:** Detect the Manipulation. Verify the Origin. Alert. Report.

The product must communicate uncertainty clearly. An AI prediction is evidence to consider, not definitive proof that media is fake or genuine.

## 2. Problem Statement

Manipulated images and videos can be shared as authentic content and mislead viewers. Users need a practical way to examine suspicious media, understand what automated checks indicate, and identify reasonable next steps before trusting or sharing it.

T.R.A.C.E. addresses this need through a focused media-analysis workflow. The prototype is not intended to make definitive legal determinations or automatically accuse people of wrongdoing.

## 3. Product Goals

1. Let a user submit an image for analysis.
2. Run a real, suitable pretrained manipulation-detection model and display its actual output.
3. Check available provenance or authenticity evidence where feasible, keeping those findings separate from AI detection results.
4. Explain findings and limitations through a clear results view and T.R.A.C.E. ALERT.
5. If feasible within the hackathon, help a user prepare an evidence-based report and navigate to an official reporting channel.

## 4. Target Users and Primary Use Case

**Target users:** People who encounter suspicious digital media and want additional evidence before trusting or sharing it.

**Primary use case:**
1. The user uploads an image.
2. T.R.A.C.E. validates the file and analyzes it with the configured model.
3. The system displays the model's actual result, relevant limitations, and any completed provenance checks.
4. T.R.A.C.E. presents a caution message appropriate to the available evidence.
5. If reporting support is implemented, the user reviews a generated evidence summary and chooses whether to use an official reporting channel.

Video analysis is a stretch goal, not a prerequisite for the initial MVP.

## 5. Scope and Priorities

### 5.1 MVP — Must Have

- A simple interface for uploading an image.
- Backend handling of the upload with file validation and safe temporary-file handling.
- Integration of a suitable pretrained image-manipulation detection model, selected and tested before being treated as a project dependency.
- Display of the model's actual output with wording that avoids claiming certainty.
- Clear handling of unsupported files, invalid uploads, and inference errors.
- A basic T.R.A.C.E. ALERT that explains the result and recommends appropriate caution.
- A usable local demonstration path.

### 5.2 Should Have — If Time Allows

- Inspection of available media metadata.
- A provenance or Content Credentials check using compatible tooling, if feasible.
- A basic evidence report that summarizes observed results and their limitations.
- A link or guidance to an appropriate official reporting channel.
- Improved results dashboard and clearer evidence presentation.

### 5.3 Stretch Goals — Only After the MVP Works

- Video upload and frame extraction.
- Frame-level analysis and timestamps, if supported by the implemented pipeline.
- Visual heatmaps or explanations, only if supported by the chosen model or a validated explainability method.
- Persistent analysis history.
- Cloud deployment.

### 5.4 Out of Scope for the Initial MVP

- Claiming pixel-level manipulation boundaries without a model that supports localization.
- Treating missing provenance credentials as proof that media is fake.
- Treating valid provenance credentials as proof that the depicted content is truthful.
- Automatically submitting reports to authorities without an authorized, verified integration.
- Automatically accusing a named person of a crime based on a model result.
- Inventing model outputs, confidence values, accuracy figures, or test results.
- Building user accounts or a database unless a demonstrated requirement makes them necessary.

## 6. Functional Requirements

### FR-01: Image Upload
The user can select and submit an image in a supported format. The application validates the file type and size before analysis and returns a useful error for invalid or unsupported uploads.

### FR-02: AI Manipulation Analysis
The backend runs a configured pretrained model on the uploaded image. The interface presents the model output faithfully and does not substitute mock or fabricated predictions for inference results.

### FR-03: Results Presentation
The result view distinguishes model output from other checks. It explains that the result is an estimate and may be wrong, especially on media types or manipulation methods outside the model's validated scope.

### FR-04: T.R.A.C.E. ALERT
The application presents a concise caution message grounded in completed checks. Example wording may include:
- “Caution: Potential media manipulation detected.”
- “Authenticity not established.”
- “No strong signs detected by the available checks.”
- “Inconclusive: Further verification recommended.”

The final message must reflect the actual evidence and must not imply certainty unsupported by the system.

### FR-05: Provenance Checks — Conditional
If implemented, the system inspects supported provenance credentials or metadata and reports the specific status returned by the verification process. At minimum, it should distinguish verified, invalid, not found, and inconclusive where the chosen tooling supports those states. Unsupported checks must be reported as unavailable, not silently treated as a negative result.

### FR-06: Evidence Report — Conditional
If implemented, the system generates a reviewable report containing only available information, such as analysis time, source URL if supplied, model findings, provenance status if checked, and relevant limitations. The user can review the report before using it.

### FR-07: Official Reporting Guidance — Conditional
If reporting assistance is implemented, the system directs the user to an appropriate official reporting channel. For an India-focused implementation, the National Cyber Crime Reporting Portal is a candidate channel: https://cybercrime.gov.in/. This is user-assisted guidance, not automatic submission.

### FR-08: Error Handling
The application returns understandable errors for invalid input, unsupported media, processing failures, unavailable model resources, and unexpected backend errors. Errors must not be disguised as successful analysis.

### FR-09: Temporary Media Handling
Uploaded media should be retained only as long as needed for analysis unless a deliberate, documented feature requires otherwise. The application should avoid exposing uploaded files through public paths or logging sensitive media contents.

## 7. Non-Functional Requirements

- **Reliability:** A valid supported image should follow a consistent upload-to-result flow; failures should be explicit.
- **Honesty and interpretability:** The interface must distinguish estimates, verification results, missing evidence, and unavailable checks.
- **Usability:** The core upload and result flow should be understandable without technical knowledge.
- **Performance:** Inference should complete within the available environment's practical limits; actual timings should be measured rather than promised in advance.
- **Privacy:** Minimize retention of uploaded media and avoid unnecessary collection of personal data.
- **Maintainability:** Keep upload handling, model inference, provenance checks, and report generation separated enough to test independently.
- **Hackathon feasibility:** Prefer the smallest reliable implementation over optional infrastructure or unfinished features.

## 8. Acceptance Criteria

The MVP is considered demonstrable when all applicable criteria below pass:

1. A supported image can be uploaded through the interface.
2. The backend validates the upload before processing it.
3. The configured pretrained model is actually invoked for inference.
4. The displayed result comes from that inference, not from a hard-coded or random value.
5. The result view communicates uncertainty and avoids declaring the media definitively real or fake.
6. Invalid or unsupported files produce a clear error without being reported as successfully analyzed.
7. Model-loading or inference failures are surfaced clearly.
8. The T.R.A.C.E. ALERT is consistent with the result and does not overstate the evidence.
9. The core workflow can be demonstrated locally using documented setup steps.
10. Any provenance or reporting features shown in the demo have been implemented and tested; otherwise, they are clearly marked as unavailable or future work.

## 9. Product Principles and Constraints

- AI detection and provenance verification are separate sources of evidence and must be displayed separately.
- Missing credentials do not establish manipulation; valid credentials do not establish truthfulness.
- A classification score is not automatically a calibrated probability of fakery.
- Visual explanations are not exact manipulation boundaries unless the underlying method explicitly supports that claim.
- No feature should be described as implemented until it has been built and tested.
- The initial deliverable is a working prototype, not a production-grade forensic or legal system.
- Keep the implementation aligned with the 24-hour constraint.

## 10. Open Decisions

These items are intentionally unresolved until validated:

- Which pretrained detection model is suitable, compatible, licensed appropriately, and practical to run.
- Supported image formats and maximum upload size.
- Final frontend and backend frameworks.
- Whether provenance verification can be integrated within the available time.
- Whether evidence-report generation fits the MVP schedule.
- Whether video analysis is feasible after image analysis works.
- Deployment target, if local demonstration is not sufficient.

Decisions should be recorded in the TDD/API specification when confirmed, and this PRD should be updated if validated constraints materially change the product scope.

---

**Current status:** Requirements draft only. This document does not assert that any feature has already been implemented or tested.
