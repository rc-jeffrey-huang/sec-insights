import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@router.get("/{file}")
async def download_file(file: str):
    download_directory = Path(UPLOAD_FOLDER)
    file_path = download_directory / file
    if file_path.is_file():
        return FileResponse(
            file_path,
            filename=file,
        )
    else:
        return {"error": "File not found"}
