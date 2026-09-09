import json

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.api_contract import UploadCaseResponse, UploadResponse
from app.services.upload_service import UploadService


router = APIRouter(tags=["upload"])
upload_service = UploadService()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="file name is required")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    content_type = file.content_type or "application/octet-stream"
    payload = upload_service.store_and_build_payload(file.filename, content, content_type)
    return UploadResponse(**payload)


@router.post("/upload-case", response_model=UploadCaseResponse)
async def upload_case(
    chart_spec: UploadFile = File(...),
    metadata: UploadFile = File(...),
    data: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
) -> UploadCaseResponse:
    if not chart_spec.filename or not metadata.filename:
        raise HTTPException(status_code=400, detail="chart_spec and metadata file names are required")
    chart_spec_content = await chart_spec.read()
    metadata_content = await metadata.read()
    if not chart_spec_content or not metadata_content:
        raise HTTPException(status_code=400, detail="chart_spec and metadata cannot be empty")

    data_content = await data.read() if data is not None else None
    image_content = await image.read() if image is not None else None
    try:
        payload = upload_service.store_case_files(
            chart_spec_filename=chart_spec.filename,
            chart_spec_content=chart_spec_content,
            metadata_filename=metadata.filename,
            metadata_content=metadata_content,
            data_filename=data.filename if data else None,
            data_content=data_content,
            image_filename=image.filename if image else None,
            image_content=image_content,
        )
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid json file content: {exc}") from exc
    return UploadCaseResponse(**payload)

