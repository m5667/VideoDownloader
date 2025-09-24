from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# serve static files (CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

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
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #6a11cb, #2575fc);
                color: white;
            }
            .container {
                background: rgba(0,0,0,0.5);
                padding: 20px;
                border-radius: 12px;
                max-width: 400px;
                width: 90%;
                text-align: center;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px;
                border: none;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            button {
                background: #ff6a00;
                border: none;
                padding: 10px 15px;
                border-radius: 8px;
                color: white;
                cursor: pointer;
                font-size: 16px;
                margin-top: 10px;
            }
            button:hover {
                background: #ff4500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎥 Video Downloader</h2>
            <form action="/info" method="get">
                <input type="text" name="url" placeholder="Paste YouTube URL here" required>
                <br>
                <button type="submit">Get Info</button>
            </form>
        </div>
    </body>
    </html>
    """