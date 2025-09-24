from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
import yt_dlp
import os
import uuid

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Downloader</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: linear-gradient(135deg, #ff6a00, #ee0979);
                color: white;
            }
            .container {
                text-align: center;
                background: rgba(0,0,0,0.4);
                padding: 20px;
                border-radius: 12px;
                width: 90%;
                max-width: 400px;
            }
            input {
                width: 100%;
                padding: 10px;
                border-radius: 8px;
                border: none;
                margin-bottom: 10px;
            }
            button {
                background: #2575fc;
                border: none;
                padding: 10px 15px;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover { background: #6a11cb; }
            .formats { margin-top: 20px; }
            a {
                display: block;
                margin: 5px 0;
                padding: 8px;
                background: #444;
                border-radius: 6px;
                color: white;
                text-decoration: none;
            }
            a:hover { background: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎥 Video Downloader</h2>
            <input type="text" id="url" placeholder="Paste YouTube URL here" />
            <button onclick="getInfo()">Fetch Formats</button>
            <div class="formats" id="formats"></div>
        </div>

        <script>
            async function getInfo() {
                const url = document.getElementById("url").value;
                if (!url) return alert("Please enter a URL");
                const res = await fetch(`/info?url=${encodeURIComponent(url)}`);
                if (!res.ok) {
                    alert("Error fetching info");
                    return;
                }
                const data = await res.json();
                const formatsDiv = document.getElementById("formats");
                formatsDiv.innerHTML = "";
                data.formats.forEach(f => {
                    const a = document.createElement("a");
                    a.href = `/download?url=${encodeURIComponent(url)}&format=${f.format_id}`;
                    a.innerText = f.ext.toUpperCase() + " - " + f.quality;
                    formatsDiv.appendChild(a);
                });
            }
        </script>
    </body>
    </html>
    """


@app.get("/info")
async def get_info(url: str = Query(...)):
    try:
        ydl_opts = {"quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()
        for f in info.get("formats", []):
            ext = f.get("ext")
            acodec = f.get("acodec")
            vcodec = f.get("vcodec")

            # Only keep MP3 (audio only) or MP4 (audio+video)
            if ext == "mp3" or (ext == "mp4" and vcodec != "none" and acodec != "none"):
                quality = f.get("format_note") or f.get("resolution") or "N/A"
                key = (ext, quality)
                if key not in seen:  # remove duplicates
                    seen.add(key)
                    formats.append({
                        "format_id": f["format_id"],
                        "ext": ext,
                        "quality": quality
                    })

        return JSONResponse({"title": info.get("title"), "formats": formats})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/download")
async def download(url: str, format: str):
    try:
        filename = f"{uuid.uuid4()}.%(ext)s"
        ydl_opts = {
            "format": format,
            "outtmpl": filename,
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        return FileResponse(downloaded_file, filename=os.path.basename(downloaded_file))

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)