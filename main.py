"""
main.py
Aplikasi FastAPI: upload lagu -> pisahkan vokal (Demucs) -> download instrumental.

Alur endpoint:
  GET  /                  -> render halaman utama
  POST /upload             -> terima file, simpan ke uploads/, balikin file_id
  POST /filter/{file_id}   -> jalankan Demucs di background, balikin status "queued"
  GET  /status/{file_id}   -> dipoll oleh frontend tiap beberapa detik
  GET  /download/{file_id} -> download hasil instrumental (no_vocals.wav)

Catatan: uploads/ dan hasil/ diperlakukan sebagai penyimpanan SEMENTARA
(seperti memori). Isinya otomatis dibersihkan setiap kali server dimatikan
(Ctrl+C) lewat lifespan handler di bawah.
"""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from processor.utils import (
    is_allowed_file,
    generate_file_id,
    safe_filename,
    clear_directory_contents,
)
from processor.filter_audio import separate_vocals

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "hasil"

# Status job disimpan di memori proses (dict biasa). Cukup untuk skripsi/demo
# single-user. Ikut hilang saat server mati — konsisten dengan uploads/hasil
# yang juga dibersihkan.
job_status: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    UPLOAD_DIR.mkdir(exist_ok=True)
    RESULT_DIR.mkdir(exist_ok=True)

    yield  # <-- aplikasi berjalan di sini

    # --- Shutdown (dipanggil otomatis saat Ctrl+C / server dihentikan) ---
    clear_directory_contents(UPLOAD_DIR)
    clear_directory_contents(RESULT_DIR)
    job_status.clear()
    print("\n[cleanup] uploads/ dan hasil/ sudah dikosongkan. Sampai jumpa!")


app = FastAPI(title="Music Vocal Filter", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Format file tidak didukung. Gunakan mp3, wav, flac, m4a, atau ogg.",
        )

    file_id = generate_file_id()
    saved_name = safe_filename(file_id, file.filename)
    dest_path = UPLOAD_DIR / saved_name

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    job_status[file_id] = {
        "status": "uploaded",
        "original_name": file.filename,
        "saved_path": str(dest_path),
        "result_path": None,
        "error": None,
    }

    return {"file_id": file_id, "filename": file.filename}


def run_separation_task(file_id: str) -> None:
    """Dijalankan di background thread oleh BackgroundTasks."""
    job = job_status.get(file_id)
    if job is None:
        return

    job["status"] = "processing"
    try:
        input_path = Path(job["saved_path"])
        result_path = separate_vocals(input_path, RESULT_DIR)
        job["result_path"] = str(result_path)
        job["status"] = "done"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.post("/filter/{file_id}")
async def filter_audio(file_id: str, background_tasks: BackgroundTasks):
    job = job_status.get(file_id)
    if job is None:
        raise HTTPException(status_code=404, detail="File tidak ditemukan. Upload dulu.")

    if job["status"] in ("processing", "queued"):
        return {"file_id": file_id, "status": job["status"]}

    job["status"] = "queued"
    job["error"] = None
    background_tasks.add_task(run_separation_task, file_id)
    return {"file_id": file_id, "status": "queued"}


@app.get("/status/{file_id}")
async def get_status(file_id: str):
    job = job_status.get(file_id)
    if job is None:
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")

    return {
        "file_id": file_id,
        "status": job["status"],
        "error": job["error"],
    }


@app.get("/download/{file_id}")
async def download_result(file_id: str):
    job = job_status.get(file_id)
    if job is None or job["status"] != "done":
        raise HTTPException(status_code=404, detail="Hasil belum siap.")

    result_path = Path(job["result_path"])
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="File hasil tidak ditemukan di server.")

    download_name = f"instrumental_{job['original_name']}".rsplit(".", 1)[0] + ".wav"
    return FileResponse(result_path, filename=download_name, media_type="audio/wav")