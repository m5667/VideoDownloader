<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>YouTube Downloader</title>
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #6a11cb, #2575fc);
      color: #fff;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
    }

    .container {
      background: rgba(0, 0, 0, 0.5);
      padding: 25px;
      border-radius: 16px;
      max-width: 400px;
      width: 100%;
      text-align: center;
      box-shadow: 0 8px 20px rgba(0,0,0,0.4);
    }

    h1 {
      font-size: 1.5rem;
      margin-bottom: 15px;
    }

    input[type="text"] {
      width: 100%;
      padding: 12px;
      border-radius: 8px;
      border: none;
      margin-bottom: 15px;
      font-size: 1rem;
    }

    button {
      background: #ff416c;
      background: linear-gradient(to right, #ff4b2b, #ff416c);
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 1rem;
      color: #fff;
      cursor: pointer;
      transition: transform 0.2s;
      margin-bottom: 15px;
    }

    button:hover {
      transform: scale(1.05);
    }

    .formats {
      margin-top: 15px;
      text-align: left;
    }

    .format-btn {
      display: block;
      width: 100%;
      margin: 6px 0;
      padding: 10px;
      border-radius: 8px;
      border: none;
      background: #2575fc;
      color: white;
      font-size: 0.95rem;
      cursor: pointer;
    }

    .format-btn:hover {
      background: #1a5edb;
    }

    /* Spinner */
    .spinner {
      display: none;
      margin: 15px auto;
      width: 40px;
      height: 40px;
      border: 4px solid rgba(255, 255, 255, 0.3);
      border-top: 4px solid #fff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      100% { transform: rotate(360deg); }
    }

  </style>
</head>
<body>
  <div class="container">
    <h1>YouTube Downloader</h1>
    <input type="text" id="url" placeholder="Paste YouTube link here">
    <button onclick="fetchInfo()">Get Formats</button>
    <div class="spinner" id="spinner"></div>
    <div id="formats" class="formats"></div>
  </div>

  <script>
    async function fetchInfo() {
      const url = document.getElementById("url").value;
      if (!url) return alert("Please enter a YouTube link.");
      
      document.getElementById("spinner").style.display = "block";
      document.getElementById("formats").innerHTML = "";

      try {
        const res = await fetch(`/info?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        document.getElementById("spinner").style.display = "none";

        if (data.error) {
          document.getElementById("formats").innerHTML = `<p style="color:red">${data.error}</p>`;
          return;
        }

        document.getElementById("formats").innerHTML = `<h3>${data.title}</h3>`;
        data.formats.forEach(fmt => {
          const btn = document.createElement("button");
          btn.className = "format-btn";
          btn.innerText = `${fmt.ext.toUpperCase()} - ${fmt.resolution}`;
          btn.onclick = () => downloadVideo(url, fmt.format_id);
          document.getElementById("formats").appendChild(btn);
        });

      } catch (err) {
        document.getElementById("spinner").style.display = "none";
        document.getElementById("formats").innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
      }
    }

    function downloadVideo(url, format) {
      window.location.href = `/download?url=${encodeURIComponent(url)}&format=${format}`;
    }
  </script>
</body>
</html>