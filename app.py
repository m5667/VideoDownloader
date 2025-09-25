from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import yt_dlp
import os
import uuid

app = FastAPI()

# Force yt-dlp to look like a real Android browser
COMMON_OPTS = {
    "quiet": True,
    "geo_bypass": True,
    "nocheckcertificate": True,
    "extractor_args": {"youtube": {"player_skip": ["js"]}},
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Mobile; rv:109.0) Gecko/117.0 Firefox/117.0"
    },
}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <title>YouTube Downloader</title>
        <style>
          body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #6a11cb, #2575fc);
            color: white;
            text-align: center;
            padding: 40px;
          }
          input {
            padding: 10px;
            width: 80%;
            max-width: 400px;
            border-radius: 12px;
            border: none;
            margin-bottom: 20px;
          }
          button {
            padding: 10px 20px;
            border-radius: 12px;
            border: none;
            background: #ff4081;
            color: white;
            font-size: 16px;
            cursor: pointer;
          }
          button:hover {
            background: #e73370;
          }
        </style>
      </head>
      <body>
        <h1>YouTube Downloader</h1>
        <form action="/info" method="get">
          <input type="text" name="url" placeholder="Paste YouTube link..." required>
          <br>
          <button type="submit">Get Formats</button>
        </form>
      </body>
    </html>
    """


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

            # Only keep MP3 (audio) and MP4 (video+audio)
            if ext == "mp3" or (ext == "m4a" and vcodec == "none"):
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

        # Deduplicate by ext + resolution
        unique = {}
        for f in formats:
            key = (f["ext"], f["resolution"])
            if key not in unique:
                unique[key] = f

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

        # Find actual file path
        if "_filename" in info:
            filename = info["_filename"]
        else:
            filename = ydl.prepare_filename(info)

        return FileResponse(
            filename,
            media_type="application/octet-stream",
            filename=os.path.basename(filename),
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)