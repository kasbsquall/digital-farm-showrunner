"""Alibaba Cloud deployment proof.

This file is the required "link to a code file showing use of Alibaba Cloud
services and APIs". It exercises Alibaba Cloud OSS (Object Storage Service)
directly so the reviewers can see a real service call, not just a mention.

Run on the ECS / Function Compute instance:
    python -m deploy.alibaba_deploy_proof

It uploads a small marker object to the configured OSS bucket and lists it back,
printing the public URL — proving the backend runs against Alibaba Cloud.
"""
import oss2

from config import settings


def prove() -> str:
    if not all([settings.oss_access_key_id, settings.oss_access_key_secret,
                settings.oss_bucket, settings.oss_endpoint]):
        raise RuntimeError("Set OSS_* env vars before running the deploy proof.")

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    key = "deploy-proof/marker.txt"
    bucket.put_object(key, b"Digital Farm Showrunner running on Alibaba Cloud OSS.")

    exists = bucket.object_exists(key)
    url = f"https://{settings.oss_bucket}.{settings.oss_endpoint.replace('https://', '')}/{key}"
    print(f"OSS upload ok={exists} url={url}")
    return url


if __name__ == "__main__":
    prove()
