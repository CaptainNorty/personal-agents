"""
S3 helpers for Unknown Unknowns audio recordings.

The frontend uploads audio bytes directly to S3 via presigned PUT URLs — the
FastAPI server never touches the audio. After upload, the server generates a
short-lived presigned GET URL and hands it to the transcription service
(AssemblyAI), which fetches the audio itself.

Local dev uses the `personal` AWS profile (boto3.Session(profile_name=...)).
In production on EC2, set AWS_PROFILE="" in .env so boto3 falls back to the
instance role attached to the EC2 instance.
"""

from __future__ import annotations

import os
import uuid
from functools import lru_cache

import boto3
from botocore.client import Config

from app.config import settings

PRESIGNED_PUT_TTL_SECONDS = 300  # 5 minutes — enough for the recording → upload window
PRESIGNED_GET_TTL_SECONDS = 600  # 10 minutes — enough for AssemblyAI to fetch


@lru_cache(maxsize=1)
def _s3_client():
    """Cached S3 client. boto3 clients are thread-safe and meant to be reused."""
    session_kwargs: dict = {}
    if settings.aws_profile:
        session_kwargs["profile_name"] = settings.aws_profile
    else:
        # boto3 reads AWS_PROFILE from os.environ directly and treats an empty
        # string as a profile name to look up (→ ProfileNotFound). On EC2 we
        # want the default credential chain (instance role), so clear it.
        os.environ.pop("AWS_PROFILE", None)
    session = boto3.Session(**session_kwargs)
    return session.client(
        "s3",
        region_name=settings.s3_region,
        # Pin the regional endpoint — without this, presigned URLs for buckets
        # outside us-east-1 use the legacy global endpoint and return 307s.
        endpoint_url=f"https://s3.{settings.s3_region}.amazonaws.com",
        # SigV4 is required for non-us-east-1 buckets and for KMS-encrypted ones.
        config=Config(signature_version="s3v4"),
    )


def build_s3_key(user_id: uuid.UUID, prompt_id: uuid.UUID, kind: str) -> str:
    """Deterministic S3 object key for a recording.

    Layout: users/{user_id}/prompts/{prompt_id}/{kind}.webm

    Same prompt + same kind → same key, so re-uploading overwrites in place.
    That's the desired behavior for retries.
    """
    return f"users/{user_id}/prompts/{prompt_id}/{kind}.webm"


def generate_presigned_put(s3_key: str) -> str:
    """Presigned PUT URL the browser uses to upload audio directly to S3.

    No Content-Type is pinned — MediaRecorder produces audio/webm on Chrome
    and audio/mp4 on Safari, both of which we accept. AssemblyAI handles
    container detection from the audio itself.
    """
    return _s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=PRESIGNED_PUT_TTL_SECONDS,
        HttpMethod="PUT",
    )


def generate_presigned_get(s3_key: str, ttl_seconds: int = PRESIGNED_GET_TTL_SECONDS) -> str:
    """Presigned GET URL handed to AssemblyAI for transcription fetch."""
    return _s3_client().generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
        ExpiresIn=ttl_seconds,
        HttpMethod="GET",
    )
