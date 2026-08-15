"""
filter_audio.py
Modul inti untuk memisahkan vokal dari instrumental menggunakan Demucs.

Demucs dijalankan lewat subprocess (python -m demucs.separate) memakai
python interpreter yang sama dengan yang menjalankan FastAPI (sys.executable),
supaya pasti memakai venv yang benar meskipun dijalankan di server lain.
"""

import subprocess
import sys
from pathlib import Path

# Model default. "htdemucs" adalah model dasar Demucs v4 (cukup akurat, ringan
# dibanding "htdemucs_ft" yang 4x lebih lambat di CPU karena menjalankan 4 model).
DEFAULT_MODEL = "htdemucs"


def separate_vocals(input_path: Path, output_dir: Path, model: str = DEFAULT_MODEL) -> Path:
    """
    Menjalankan Demucs untuk memisahkan vokal dan instrumental dari file audio.

    Parameters
    ----------
    input_path : Path
        Path file audio sumber (hasil upload user), contoh: uploads/abc123.mp3
    output_dir : Path
        Folder tempat hasil separasi disimpan, contoh: hasil/
    model : str
        Nama model Demucs yang dipakai.

    Returns
    -------
    Path
        Path menuju file instrumental (no_vocals.wav) hasil separasi.

    Raises
    ------
    RuntimeError
        Jika proses Demucs gagal (exit code bukan 0).
    FileNotFoundError
        Jika Demucs sukses tapi file hasil tidak ditemukan di lokasi yang diharapkan.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs.separate",
        "-n", model,
        "--two-stems", "vocals",
        "-o", str(output_dir),
        str(input_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # stderr Demucs biasanya berisi pesan error yang jelas (format tidak
        # didukung, file corrupt, ffmpeg tidak ditemukan, dll).
        raise RuntimeError(f"Demucs gagal memproses file:\n{result.stderr[-2000:]}")

    # Demucs menyimpan hasil dengan struktur:
    # {output_dir}/{model}/{nama_file_tanpa_ekstensi}/vocals.wav
    # {output_dir}/{model}/{nama_file_tanpa_ekstensi}/no_vocals.wav
    stem_name = input_path.stem
    instrumental_path = output_dir / model / stem_name / "no_vocals.wav"

    if not instrumental_path.exists():
        raise FileNotFoundError(
            f"Demucs selesai tapi file hasil tidak ditemukan di: {instrumental_path}"
        )

    return instrumental_path