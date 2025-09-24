from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import yt_dlp
import os

app = FastAPI()

COOKIES_FILE = "cookies.txt"  # place cookies.txt in root (Render supports it)


# ✅ Extract video info
@app.get("/info")
def get_info(url: str = Query(...)):
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "cookies": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            formats = []
            for f in info.get("formats", []):
                ext = f.get("ext")

                # Keep only MP3 (audio) + MP4 (video+audio)
                if ext in ["mp4", "m4a"]:
                    if f.get("vcodec") != "none" and f.get("acodec") != "none":
                        fmt_type = "mp4"
                    elif f.get("vcodec") == "none":
                        fmt_type = "mp3"
                    else:
                        continue

                    formats.append({
                        "format_id": f["format_id"],
                        "ext": fmt_type,
                        "resolution": f.get("resolution") or f"{f.get('width')}x{f.get('height')}" if f.get("width") else None,
                        "abr": f.get("abr"),
                        "tbr": f.get("tbr"),
                    })

            # ✅ Remove duplicates
            seen = set()
            clean_formats = []
            for f in formats:
                if f["format_id"] not in seen:
                    clean_formats.append(f)
                    seen.add(f["format_id"])

            return {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "formats": clean_formats
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ✅ Download selected format
@app.get("/download")
def download(url: str, format: str):
    try:
        ydl_opts = {
            "format": format,
            "cookies": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            "outtmpl": "%(title)s.%(ext)s"
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        return FileResponse(
            path=filename,
            filename=os.path.basename(filename),
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))