"""Lưu, sao chép, xoá ảnh của một extraction trên đĩa: storage_dir/<id>/<index>.webp."""
import shutil
from pathlib import Path

from ..storage.models import ImageRecord
from .optimize import OptimizedImage


def save_images(storage_dir: Path, extraction_id: str, images: list[OptimizedImage]) -> list[ImageRecord]:
    folder = Path(storage_dir) / extraction_id
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for index, image in enumerate(images):
        (folder / f"{index}.webp").write_bytes(image.data)
        records.append(ImageRecord(
            index=index,
            path=f"{extraction_id}/{index}.webp",
            width=image.width,
            height=image.height,
            bytes=len(image.data),
        ))
    return records


def copy_images(storage_dir: Path, src_id: str, dst_id: str, records: list[ImageRecord]) -> list[ImageRecord]:
    """Sao chép ảnh của extraction gốc sang extraction mới (chạy lại)."""
    folder = Path(storage_dir) / dst_id
    folder.mkdir(parents=True, exist_ok=True)
    copied = []
    for record in records:
        shutil.copyfile(image_file(storage_dir, record), folder / f"{record.index}.webp")
        copied.append(ImageRecord(
            index=record.index,
            path=f"{dst_id}/{record.index}.webp",
            width=record.width,
            height=record.height,
            bytes=record.bytes,
        ))
    return copied


def delete_images(storage_dir: Path, extraction_id: str) -> None:
    shutil.rmtree(Path(storage_dir) / extraction_id, ignore_errors=True)


def image_file(storage_dir: Path, record: ImageRecord) -> Path:
    return Path(storage_dir) / record.path
