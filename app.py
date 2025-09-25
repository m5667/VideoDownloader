from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import yt_dlp

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Helper: filter formats
def filter_formats(info):
    video_formats = []
    audio_formats = []
    for f in info.get("formats", []):
        if f.get("acodec") != "none" and f.get("vcodec") == "none":
            # Audio only
            audio_formats.append({
                "format_id": f["format_id"],
                "ext": f["ext"],
                "url": f["url"],
                "abr": f.get("abr")
            })
        elif f.get("acodec") != "none" and f.get("vcodec") != "none":
            # Video+audio
            video_formats.append({
                "format_id": f["format_id"],
                "ext": f["ext"],
                "url": f["url"],
                "height": f.get("height"),
                "fps": f.get("fps")
            })
    return video_formats, audio_formats

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
            data = {"title": info.get("title")}

            video_formats, audio_formats = filter_formats(info)
            data["mp4_formats"] = [f for f in video_formats if f["ext"] == "mp4"]
            data["mp3_formats"] = [f for f in audio_formats if f["ext"] == "mp3"]
            return JSONResponse(content=data)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))