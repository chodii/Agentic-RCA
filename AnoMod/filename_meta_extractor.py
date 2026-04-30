# -*- coding: utf-8 -*-
"""
Created on Tue Apr 28 01:32:15 2026

@author: chodo
"""

from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import shutil

ZIP_PATH = Path(r"C:\\Users\\chodo\\Downloads\\AnoMod.zip")
OUT_DIR = Path(r"C:\\Datasets\\AnoMod_safe\\")
DATA_DIR = OUT_DIR / "data"
MANIFEST_PATH = OUT_DIR / "manifest.jsonl"

def safe_ext(name: str) -> str:
    ext = Path(name).suffix
    if not ext or len(ext) > 20:
        return ".bin"
    ext = re.sub(r"[^A-Za-z0-9._-]", "_", ext)
    return ext

def parse_label_from_name(original_name: str):
    """
    TODO: replace this with AnoMod-specific parsing.
    For now, keep full original path as label source.
    """
    stem = Path(original_name).stem
    return {
        "raw_stem": stem,
        "original_name": original_name,
    }

def extract_zip_safely(zip_path: Path, data_dir: Path, manifest_path: Path):
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "r") as zf, manifest_path.open("w", encoding="utf-8") as mf:
        for i, info in enumerate(zf.infolist()):
            original = info.filename

            # Skip directories
            if original.endswith("/"):
                continue

            # Basic zip-slip protection
            if original.startswith("/") or ".." in Path(original).parts:
                print(f"Skipping suspicious path: {original}")
                continue

            h = hashlib.sha1(original.encode("utf-8", errors="replace")).hexdigest()
            ext = safe_ext(original)
            safe_name = f"{i:08d}_{h[:12]}{ext}"
            safe_path = data_dir / safe_name

            with zf.open(info, "r") as src, safe_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)

            rec = {
                "safe_path": str(safe_path),
                "safe_name": safe_name,
                "original_zip_name": original,
                "sha1_original_name": h,
                "file_size": info.file_size,
                "label_info": parse_label_from_name(original),
            }

            mf.write(json.dumps(rec, ensure_ascii=False) + "\n")

extract_zip_safely(ZIP_PATH, DATA_DIR, MANIFEST_PATH)