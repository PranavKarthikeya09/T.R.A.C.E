"""Image analysis endpoint."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from app.schemas.analysis import AnalysisResponse
from app.schemas.error import ErrorResponse, ErrorDetail
from app.utils.media import validate_image_upload
from app.adapters.exceptions import (
    ModelUnavailableException,
    ModelAuthenticationException,
    ModelRateLimitException,
    ModelNetworkException,
    ModelInferenceException,
)
from app.services.analysis_service import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()


@router.post(
    "/analyze/image",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    }
)
async def analyze_image(
    file: UploadFile = File(None),
    include_provenance: bool = Form(default=False)
):
    """
    Upload and analyze one image using the configured detection model.
    Adheres strictly to API_SPEC.md Section 4 & 5.
    """
    if file is None or not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(code="MISSING_FILE", message="Image file is required for analysis.")
            ).model_dump()
        )

    content = await file.read()
    if not content:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(code="MISSING_FILE", message="Uploaded file is empty.")
            ).model_dump()
        )

    is_valid, error_code, pil_image = validate_image_upload(file.filename, content)

    if not is_valid:
        if error_code == "FILE_TOO_LARGE":
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=ErrorResponse(
                    error=ErrorDetail(code="FILE_TOO_LARGE", message="Uploaded file exceeds maximum size limit.")
                ).model_dump()
            )
        elif error_code == "UNSUPPORTED_MEDIA_TYPE":
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content=ErrorResponse(
                    error=ErrorDetail(code="UNSUPPORTED_MEDIA_TYPE", message="Please upload a supported image format (JPEG, PNG, WebP).")
                ).model_dump()
            )
        elif error_code == "INVALID_IMAGE":
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=ErrorResponse(
                    error=ErrorDetail(code="INVALID_IMAGE", message="Uploaded file could not be decoded as a valid image.")
                ).model_dump()
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    error=ErrorDetail(code="INVALID_REQUEST", message="Invalid upload request.")
                ).model_dump()
            )

    try:
        result = await analysis_service.analyze_image_async(
            filename=file.filename,
            image=pil_image,
            include_provenance=include_provenance
        )
        return result
    except ModelUnavailableException:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MODEL_UNAVAILABLE",
                    message="Detection model is currently unavailable or not yet configured for inference."
                )
            ).model_dump()
        )
    except ModelRateLimitException:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MODEL_UNAVAILABLE",
                    message="Inference service is currently rate-limited. Please retry shortly."
                )
            ).model_dump()
        )
    except (ModelAuthenticationException, ModelNetworkException):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MODEL_UNAVAILABLE",
                    message="Inference service could not be reached. Please check service configuration."
                )
            ).model_dump()
        )
    except ModelInferenceException:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INFERENCE_FAILED",
                    message="Model inference failed to produce a valid analysis."
                )
            ).model_dump()
        )
    except RuntimeError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MODEL_UNAVAILABLE",
                    message="Detection model is currently unavailable or not yet configured for inference."
                )
            ).model_dump()
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INFERENCE_FAILED",
                    message="An unexpected error occurred during media analysis."
                )
            ).model_dump()
        )
