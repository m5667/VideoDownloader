from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import yt_dlp
import os
import uuid

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# yt-dlp common options
COMMON_OPTS = {
    "quiet": True,
    "geo_bypass": True,
    "nocheckcertificate": True,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Mobile; rv:109.0) Gecko/117.0 Firefox/117.0"
    },
}

# Optional cookies file support (upload cookies.txt into /app/cookies.txt)
COOKIES_FILE = "cookies.txt"
if os.path.exists(COOKIES_FILE):
    COMMON_OPTS["cookies"] = COOKIES_FILE


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/info")
def get_info(url: str = Query(..., description="YouTube URL")):
    try:
        ydl_opts = {**COMMON_OPTS, "dump_single_json": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info.get("formats", []):
            if not f.get("filesize"):
                continue
            ext = f.get("ext")
            acodec = f.get("acodec")
            vcodec = f.get("vcodec")

            if ext in ["mp3", "m4a"] and vcodec == "none":
                formats.append({
                    "format_id": f["format_id"],
                    "ext": "mp3",
                    "resolution": "Audio only",
                    "filesize": f["filesize"]
                })
            elif ext == "mp4" and vcodec != "none" and acodec != "none":
                formats.append({
                    "format_id": f["format_id"],
                    "ext": "mp4",
                    "resolution": f.get("resolution") or f"{f.get('height', '')}p",
                    "filesize": f["filesize"]
                })

        unique = {(f["ext"], f["resolution"]): f for f in formats}
        return JSONResponse({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "formats": list(unique.values())
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/download")
def download(url: str, format_id: str):
    try:
        temp_file = f"/tmp/{uuid.uuid4()}.%(ext)s"
        ydl_opts = {**COMMON_OPTS, "outtmpl": temp_file, "format": format_id}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        filename = info.get("_filename", ydl.prepare_filename(info))

        return FileResponse(
            filename,
            media_type="application/octet-stream",
            filename=os.path.basename(filename),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)