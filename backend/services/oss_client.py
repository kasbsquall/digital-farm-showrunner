"""Alibaba Cloud OSS: persist generated videos to a permanent public URL.

DashScope returns a *temporary* signed URL for generated videos. We download it
and re-upload to our own bucket so the frontend feed has a stable, public link.
"""
import hashlib

import httpx
import oss2

from config import settings


def _bucket() -> oss2.Bucket:
    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    return oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)


def is_configured() -> bool:
    return all(
        [settings.oss_access_key_id, settings.oss_access_key_secret,
         settings.oss_bucket, settings.oss_endpoint]
    )


def public_url(key: str) -> str:
    host = settings.oss_endpoint.replace("https://", "").replace("http://", "")
    return f"https://{settings.oss_bucket}.{host}/{key}"


def _persist(src_url: str, prefix: str, ext: str, content_type: str) -> str:
    resp = httpx.get(src_url, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    key = f"{prefix}/{hashlib.sha1(src_url.encode()).hexdigest()[:12]}.{ext}"
    _bucket().put_object(key, resp.content, headers={"Content-Type": content_type})
    return public_url(key)


def persist_video(src_url: str) -> str:
    """Download a video from src_url and upload it to OSS. Returns the public URL."""
    return _persist(src_url, "episodes", "mp4", "video/mp4")


def persist_image(src_url: str, prefix: str = "images") -> str:
    """Download an image from src_url and upload it to OSS. Returns the public URL."""
    return _persist(src_url, prefix, "png", "image/png")


def persist_local(path: str, prefix: str = "episodes", ext: str = "mp4",
                  content_type: str = "video/mp4") -> str:
    """Upload a LOCAL file (e.g. a stitched multi-shot video) to OSS. Returns the URL."""
    with open(path, "rb") as f:
        data = f.read()
    key = f"{prefix}/{hashlib.sha1(data).hexdigest()[:12]}.{ext}"
    _bucket().put_object(key, data, headers={"Content-Type": content_type})
    return public_url(key)
