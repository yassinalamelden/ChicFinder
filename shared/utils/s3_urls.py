"""
shared/utils/s3_urls.py
========================
Builds public URLs for catalog images in the CatalogImages S3 bucket
(public-read, see infrastructure/cdk/chicfinder_constructs/storage.py).

RDS stores only the object key (`image_key`); anything serving that key to a
client needs the full URL, so both the API's /stores routes and the remote
index builder resolve it through here rather than each formatting their own.
"""

from __future__ import annotations

import os

DEFAULT_REGION = "eu-central-1"


def public_image_url(
    image_key: str | None,
    bucket_name: str | None = None,
    region: str | None = None,
) -> str | None:
    """Returns the public https URL for a catalog image key, or None if the
    key or bucket is missing (local dev has no bucket configured)."""
    if not image_key:
        return None

    bucket = bucket_name or os.getenv("S3_BUCKET_NAME")
    if not bucket:
        return None

    resolved_region = (
        region
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_REGION
    )
    return f"https://{bucket}.s3.{resolved_region}.amazonaws.com/{image_key}"
