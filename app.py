from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI()

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Temporary download folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/info")
async def video_info(url: str):
    """
    Fetch video or playlist metadata
    """
    ydl_opts = {"quiet": True, "skip_download": True, "extract_flat": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download_video(url: str, format: str = "best"):
    """
    Provide direct download URL for browser
    """
    filename = os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s")
    ydl_opts = {"outtmpl": filename, "format": format, "quiet": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            file_path = os.path.join(DOWNLOAD_FOLDER, f"{info['title']}.{info['ext']}")
            return FileResponse(file_path, filename=f"{info['title']}.{info['ext']}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))