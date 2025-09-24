from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import uuid

app = FastAPI()

# serve frontend from static/
app.mount("/", StaticFiles(directory="static", html=True), name="static")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@app.get("/api/info")
async def get_info(url: str):
    """Fetch video or playlist info"""
    try:
        ydl_opts = {"quiet": True, "skip_download": True, "extract_flat": False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if "entries" in info:  # playlist
                return {
                    "playlist": True,
                    "title": info.get("title"),
                    "entries": [
                        {
                            "id": e.get("id"),
                            "title": e.get("title"),
                            "thumbnail": e.get("thumbnail"),
                            "url": f"https://www.youtube.com/watch?v={e.get('id')}"
                        }
                        for e in info["entries"] if e
                    ]
                }

            # single video
            return {
                "playlist": False,
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "formats": [
                    {
                        "format_id": f["format_id"],
                        "ext": f["ext"],
                        "res": f.get("resolution") or f.get("format")
                    }
                    for f in info["formats"]
                    if f.get("ext") in ["mp4", "m4a", "webm", "mp3"]
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download")
async def download_video(url: str, format_id: str):
    """Download selected format"""
    try:
        filename = f"{uuid.uuid4()}.%(ext)s"
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        ydl_opts = {
            "format": format_id,
            "outtmpl": filepath,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_path = ydl.prepare_filename(info)

        return FileResponse(final_path, filename=info.get("title", "video") + "." + final_path.split(".")[-1])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
