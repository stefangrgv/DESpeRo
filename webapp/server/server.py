import logging
from fastapi import FastAPI, UploadFile, File
from fastapi import FastAPI, Request, Response
import uvicorn
import os
from pathlib import Path
from typing import List

API_VERSION = "v1"

app = FastAPI()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@app.get(f"api/{API_VERSION}/healthcheck/")
async def healthcheck():
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    uploads_dir = Path("./uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        contents = await file.read()
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(contents)

    return [{
        "filename": file.filename,
        "content_type": file.content_type
    } for file in files]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("SERVER_PORT", "8001")))
