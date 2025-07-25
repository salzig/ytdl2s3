#!/usr/bin/env python
import os
import uvicorn
import fastapi
import yt_dlp
import minio




BASE_DIR = os.environ.get("BASE_DIR", os.path.abspath(os.path.dirname(__file__)))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

S3_HOST = os.environ.get("S3_HOST", "localhost:9000")
S3_CLIENT = os.environ.get("S3_CLIENT", "root")
S3_KEY = os.environ.get("S3_KEY", "password")
S3_BUCKET = os.environ.get("S3_BUCKET", "ytdlp2s3")

print("Starting up the server...")
print("Download Directory: ", DOWNLOAD_DIR)

if not os.path.exists(DOWNLOAD_DIR):
    print("Creating download directory...")
    os.makedirs(DOWNLOAD_DIR)

if not os.path.exists(TEMP_DIR):
    print("Creating temp directory...")
    os.makedirs(TEMP_DIR)

s3 = minio.Minio(
  S3_HOST,
  S3_CLIENT,
  S3_KEY,
  secure=False
)
s3.bucket_exists(S3_BUCKET) or s3.make_bucket(S3_BUCKET)

app = fastapi.FastAPI()

@app.get("/", response_class=fastapi.responses.PlainTextResponse)
def greetings():
    return f"Greetings Dr. Falken"

@app.get("/health", response_class=fastapi.responses.PlainTextResponse)
def health():
    return f"OK"

@app.get("/v1/fetch")
def fetch(url: str):
  ytdlp_options = {
    'paths': {
      'home': DOWNLOAD_DIR,
      'temp': TEMP_DIR,
    },
  }

  with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
    info_dict = ydl.extract_info(url, download=True)

    downloaded_files = [item['filename'] for item in info_dict['requested_downloads']]
    uploaded_files = []

    for file in downloaded_files:
      basename = os.path.basename(file)
      try:
        s3.fput_object(S3_BUCKET, basename, file)
        uploaded_files.append(basename)
      except minio.error.MinioException as e:
        print(f"Error uploading {basename} to S3: {e}")
      finally:
        os.remove(file)

    return {
      "host": S3_HOST,
      "bucket": S3_BUCKET,
      "files": uploaded_files
    }

  return "hu?"

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=1337, log_level="info")
