"""Local-disk storage for user-uploaded content (product images).

A local directory, served via FastAPI's `StaticFiles` (mounted in
`app.main`), is the simplest thing that works at dev/demo scale. If this
ever needs to run across multiple app instances or scale past a single
disk, swap this module for an S3-backed implementation - callers only
depend on `save_product_image`'s signature, not where the bytes end up.
"""

from pathlib import Path

from app.core.config import get_settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def content_type_extension(content_type: str) -> str | None:
    """Return the file extension for an accepted image content type, or
    None if the content type isn't one of the accepted image formats."""
    return _ALLOWED_CONTENT_TYPES.get(content_type)


def save_product_image(product_id: int, contents: bytes, extension: str) -> str:
    """Write an image to disk and return the URL it's served from."""
    products_dir = Path(get_settings().upload_dir) / "products"
    products_dir.mkdir(parents=True, exist_ok=True)
    (products_dir / f"{product_id}{extension}").write_bytes(contents)
    return f"/static/products/{product_id}{extension}"
