from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import logging
from pathlib import Path
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Downloader", description="Lightweight YouTube Downloader")

# Serve the main HTML file
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    html_file = Path("index.html")
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(), status_code=200)
    else:
        # Return embedded HTML if file doesn't exist
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Video Downloader</title></head>
        <body>
            <h1>Video Downloader</h1>
            <p>Please create an index.html file or use the embedded version.</p>
        </body>
        </html>
        """, status_code=200)

class VideoDownloader:
    def __init__(self):
        self.ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

    def extract_video_info(self, url):
        """Extract video information without downloading"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    # It's a playlist
                    return self.format_playlist_info(info)
                else:
                    # It's a single video
                    return self.format_video_info(info)
                    
        except Exception as e:
            logger.error(f"Error extracting info: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error processing URL: {str(e)}")

    def format_video_info(self, info):
        """Format single video information"""
        formats = []
        for f in info.get('formats', []):
            if f.get('ext') in ['mp4', 'webm'] and f.get('height'):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f"{f.get('height')}p",
                    'filesize': f.get('filesize', 0),
                    'url': f.get('url')
                })
        
        return {
            'type': 'video',
            'title': info.get('title', 'Unknown Title'),
            'uploader': info.get('uploader', 'Unknown'),
            'duration': self.format_duration(info.get('duration')),
            'view_count': info.get('view_count', 0),
            'formats': formats,
            'url': info.get('webpage_url', url)
        }

    def format_playlist_info(self, info):
        """Format playlist information"""
        videos = []
        for entry in info['entries'][:20]:  # Limit to first 20 videos
            if entry:
                video_formats = []
                if 'formats' in entry:
                    for f in entry.get('formats', []):
                        if f.get('ext') in ['mp4', 'webm'] and f.get('height'):
                            video_formats.append({
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'resolution': f"{f.get('height')}p",
                                'url': f.get('url')
                            })
                
                videos.append({
                    'title': entry.get('title', 'Unknown Title'),
                    'duration': self.format_duration(entry.get('duration')),
                    'url': entry.get('webpage_url', ''),
                    'formats': video_formats
                })
        
        return {
            'type': 'playlist',
            'title': info.get('title', 'Unknown Playlist'),
            'uploader': info.get('uploader', 'Unknown'),
            'video_count': len(info.get('entries', [])),
            'videos': videos
        }

    def format_duration(self, duration):
        """Format duration in seconds to readable format"""
        if not duration:
            return 'Unknown'
        
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def get_download_url(self, video_url, quality='best', format_type='mp4'):
        """Get direct download URL for the video"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            # Set format based on requirements
            if format_type == 'mp3':
                ydl_opts['format'] = 'bestaudio/best'
            else:
                if quality == 'best':
                    ydl_opts['format'] = 'best[ext=mp4]/best'
                elif quality == 'worst':
                    ydl_opts['format'] = 'worst[ext=mp4]/worst'
                else:
                    # Extract height from quality (e.g., '720p' -> '720')
                    height = re.findall(r'\d+', quality)
                    if height:
                        height = height[0]
                        ydl_opts['format'] = f'best[height<={height}][ext=mp4]/best[height<={height}]/best[ext=mp4]/best'
                    else:
                        ydl_opts['format'] = 'best[ext=mp4]/best'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                # Return the URL of the best matching format
                if 'url' in info:
                    return info['url']
                elif 'formats' in info and info['formats']:
                    # Find the best format that matches our criteria
                    for fmt in reversed(info['formats']):
                        if fmt.get('url'):
                            return fmt['url']
                
                raise Exception("No suitable format found")
                
        except Exception as e:
            logger.error(f"Error getting download URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")

# Initialize the downloader
downloader = VideoDownloader()

@app.post("/api/info")
async def get_video_info(request: Request):
    """Get video or playlist information"""
    try:
        data = await request.json()
        url = data.get("url")
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Validate YouTube URL
        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL")
        
        info = downloader.extract_video_info(url)
        return JSONResponse(content=info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_video_info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/download")
async def download_video(url: str, quality: str = "best", format: str = "mp4"):
    """Get direct download URL and redirect to it"""
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL parameter is required")
        
        # Validate YouTube URL
        if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
            raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL")
        
        # Get the direct download URL
        download_url = downloader.get_download_url(url, quality, format)
        
        # Redirect to the direct download URL
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Video Downloader API is running"}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": "The requested resource was not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "Something went wrong"}
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Video Downloader API started successfully!")
    logger.info("📱 Mobile-optimized YouTube downloader ready")

# Shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Video Downloader API shutting down...")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or default to 10000
    port = int(os.environ.get("PORT", 10000))
    
    logger.info(f"Starting server on port {port}")
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        log_level="info"
    )