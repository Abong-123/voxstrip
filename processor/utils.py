"""
utils.py
Fungsi bantu kecil: validasi ekstensi file, pembuatan ID unik per upload,
dan pembersihan folder sementara (uploads/ & hasil/).
"""

import shutil
import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


def is_allowed_file(filename: str) -> bool:
    """Cek apakah ekstensi file termasuk yang didukung."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def generate_file_id() -> str:
    """Buat ID unik pendek untuk setiap file yang diupload."""
    return uuid.uuid4().hex[:12]


def safe_filename(file_id: str, original_filename: str) -> str:
    """Gabungkan ID unik dengan ekstensi asli agar nama file aman & tidak bentrok."""
    ext = Path(original_filename).suffix.lower()
    return f"{file_id}{ext}"


def clear_directory_contents(directory: Path) -> None:
    """
    Hapus semua isi folder KECUALI file .gitkeep.

    Dipakai untuk mengosongkan uploads/ dan hasil/ setiap kali aplikasi
    dimatikan (Ctrl+C) — folder tersebut diperlakukan sebagai penyimpanan
    sementara, bukan penyimpanan permanen.
    """
    if not directory.exists():
        return

    for item in directory.iterdir():
        if item.name == ".gitkeep":
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except OSError:
            # File mungkin masih terkunci (misal masih dibaca proses lain di
            # Windows). Tidak fatal — lanjutkan membersihkan item lainnya.
            pass