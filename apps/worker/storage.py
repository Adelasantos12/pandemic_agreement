import os
import requests
import boto3
import uuid
import yt_dlp
from botocore.exceptions import NoCredentialsError

# Environment variables for S3
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET")
STORAGE_ENDPOINT = os.environ.get("STORAGE_ENDPOINT")
STORAGE_ACCESS_KEY = os.environ.get("STORAGE_ACCESS_KEY")
STORAGE_SECRET_KEY = os.environ.get("STORAGE_SECRET_KEY")

def get_s3_client():
    if not STORAGE_ENDPOINT:
        return None
    return boto3.client(
        's3',
        endpoint_url=STORAGE_ENDPOINT,
        aws_access_key_id=STORAGE_ACCESS_KEY,
        aws_secret_access_key=STORAGE_SECRET_KEY
    )

def download_to_tmp(path_or_url: str) -> str:
    """
    Downloads a file from S3 (if key) or HTTP URL (if url) to /tmp.
    For YouTube/Video URLs, uses yt-dlp to download audio.
    Returns the local file path.
    """
    tmp_filename = f"/tmp/{uuid.uuid4()}"

    # Check if it's a URL
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        # Check if it might be a video site (simple heuristic)
        if "youtube.com" in path_or_url or "youtu.be" in path_or_url:
            return download_video_audio(path_or_url, tmp_filename)

        # Regular HTTP download
        try:
            response = requests.get(path_or_url, stream=True)
            response.raise_for_status()
            # Try to infer extension
            content_type = response.headers.get('content-type', '')
            ext = ""
            if "pdf" in content_type:
                ext = ".pdf"
            elif "audio" in content_type:
                ext = ".mp3" # simplified

            final_path = tmp_filename + ext
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return final_path
        except Exception as e:
            raise RuntimeError(f"Failed to download URL {path_or_url}: {e}")

    # Assume it's an S3 key
    else:
        s3 = get_s3_client()
        if not s3:
            # If no S3 config, maybe it's a local file path for testing?
            if os.path.exists(path_or_url):
                return path_or_url
            raise RuntimeError("S3 client not configured and not a URL")

        try:
            # maintain extension if present in key
            _, ext = os.path.splitext(path_or_url)
            final_path = tmp_filename + ext
            s3.download_file(STORAGE_BUCKET, path_or_url, final_path)
            return final_path
        except Exception as e:
            raise RuntimeError(f"Failed to download from S3 {path_or_url}: {e}")

def download_video_audio(url: str, output_base: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_base,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_base + ".mp3"
