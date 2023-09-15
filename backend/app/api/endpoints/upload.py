import os
import shutil

from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@router.post("")
async def upload_file(file: UploadFile):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as pdf_file:
            shutil.copyfileobj(file.file, pdf_file)
        return JSONResponse(
            content={"message": f"文件 {file.filename} 已上传成功."}, status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"error": f"上传文件时出错: {str(e)}"}, status_code=500)
