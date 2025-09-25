import yt_dlp  # Add this import

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Remove the StaticFiles mounting line if not using static files
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper: filter formats for MP4/MP3
def filter_formats(info):
    video_formats = []
    audio_formats = []
    for f in info.get("formats", []):
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            # Audio only
            audio_formats.append({
                "format_id": f["format_id"],
                "ext": f["ext"],
                "abr": f.get("abr")
            })
        elif f.get("acodec") != "none" and f.get("vcodec") != "none":
            # Video+audio
            video_formats.append({
                "format_id": f["format_id"],
                "ext": f["ext"],
                "height": f.get("height"),
                "fps": f.get("fps")
            })
    # Remove duplicates by format_id
    video_formats = {f['format_id']: f for f in video_formats}.values()
    audio_formats = {f['format_id']: f for f in audio_formats}.values()
    return list(video_formats), list(audio_formats)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/info")
async def get_info(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    try:
        ydl_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            is_playlist = "entries" in info
            data = {"title": info.get("title"), "is_playlist": is_playlist}

            if is_playlist:
                # Playlist: show MP4 only
                videos = []
                for entry in info["entries"]:
                    v_formats, _ = filter_formats(entry)
                    # Only MP4 video+audio
                    mp4_formats = [f for f in v_formats if f["ext"] == "mp4"]
                    videos.append({
                        "title": entry.get("title"),
                        "formats": mp4_formats
                    })
                data["videos"] = videos
            else:
                # Single video: show both MP4 and MP3
                v_formats, a_formats = filter_formats(info)
                data["mp4_formats"] = [f for f in v_formats if f["ext"] == "mp4"]
                data["mp3_formats"] = [f for f in a_formats if f["ext"] == "mp3"]
            return JSONResponse(content=data)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download(url: str, format_id: str):
    if not url or not format_id:
        raise HTTPException(status_code=400, detail="URL and format required")
    try:
        ydl_opts = {
            "format": format_id,
            "quiet": True,
            "no_warnings": True,
            "outtmpl": "downloads/%(title)s.%(ext)s"
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)
            return FileResponse(filename, filename=info["title"] + "." + info["ext"])
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))