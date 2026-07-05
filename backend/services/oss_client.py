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


def persist_video(src_url: str) -> str:
    """Download a video from src_url and upload it to OSS. Returns the public URL."""
    resp = httpx.get(src_url, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    key = f"episodes/{hashlib.sha1(src_url.encode()).hexdigest()[:12]}.mp4"
    _bucket().put_object(key, resp.content, headers={"Content-Type": "video/mp4"})
    return public_url(key)
