from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import tempfile
import json
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
        # Create a temporary cookie file
        self.cookie_file = self.create_temp_cookie_file()
        
        self.ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Cookie handling
            'cookiefile': self.cookie_file,
            'cookiesfrombrowser': ('chrome',),  # Try to use browser cookies
            # Advanced anti-bot detection
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash'],
                    'player_skip': ['configs'],
                    'comment_sort': ['top'],
                    'max_comments': [0],
                }
            },
            # Realistic browser headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            # Rate limiting and delays
            'sleep_interval': 2,
            'max_sleep_interval': 10,
            'sleep_interval_requests': 2,
            'sleep_interval_subtitles': 2,
            # Additional options
            'nocheckcertificate': True,
            'no_check_certificates': True,
            'prefer_insecure': True,
            'geo_bypass': True,
        }

    def create_temp_cookie_file(self):
        """Create a temporary cookie file with basic YouTube cookies"""
        try:
            # Create temporary file
            fd, cookie_file = tempfile.mkstemp(suffix='.txt', prefix='ytdl_cookies_')
            os.close(fd)
            
            # Write basic Netscape cookie format
            with open(cookie_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tCONSENT\tYES+cb\n")
                f.write(".youtube.com\tTRUE\t/\tFALSE\t0\tYSC\tdQw4w9WgXcQ\n")
            
            return cookie_file
        except Exception as e:
            logger.warning(f"Could not create cookie file: {e}")
            return None

    def extract_video_info(self, url):
        """Extract video information without downloading"""
        try:
            # First attempt with standard options
            with yt_dlp.YoutubeDL(self.ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    # It's a playlist
                    return self.format_playlist_info(info)
                else:
                    # It's a single video
                    return self.format_video_info(info)
                    
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific YouTube bot detection errors
            if 'sign in to confirm' in error_msg or 'not a bot' in error_msg:
                return self.extract_with_fallback(url)
            elif 'private video' in error_msg:
                raise HTTPException(status_code=400, detail="This video is private and cannot be accessed")
            elif 'video unavailable' in error_msg:
                raise HTTPException(status_code=400, detail="This video is not available")
            elif 'age-restricted' in error_msg:
                return self.extract_age_restricted(url)
            else:
                logger.error(f"Error extracting info: {str(e)}")
                raise HTTPException(status_code=400, detail="Unable to process this video. Please try a different URL.")

    def extract_with_fallback(self, url):
        """Fallback method for bot detection issues"""
        fallback_methods = [
            self.try_mobile_extraction,
            self.try_embed_extraction,
            self.try_minimal_extraction,
            self.try_invidious_extraction
        ]
        
        for method in fallback_methods:
            try:
                result = method(url)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Fallback method {method.__name__} failed: {e}")
                continue
        
        # If all methods fail, return basic info
        return self.create_basic_info(url)

    def try_mobile_extraction(self, url):
        """Try extraction with mobile user agent"""
        mobile_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            'sleep_interval': 3,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(mobile_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return self.format_basic_info(info, url)

    def try_embed_extraction(self, url):
        """Try extraction using embed URL"""
        video_id = self.extract_video_id(url)
        if not video_id:
            raise Exception("Could not extract video ID")
            
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        embed_opts = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Referer': 'https://www.google.com/',
            },
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(embed_opts) as ydl:
            info = ydl.extract_info(embed_url, download=False)
            return self.format_video_info(info) if info else None

    def try_minimal_extraction(self, url):
        """Try minimal extraction with basic options"""
        minimal_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'no_check_certificate': True,
            'geo_bypass': True,
        }
        
        with yt_dlp.YoutubeDL(minimal_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return self.format_basic_info(info, url)

    def try_invidious_extraction(self, url):
        """Try using Invidious as a fallback"""
        video_id = self.extract_video_id(url)
        if not video_id:
            raise Exception("Could not extract video ID")
            
        # Use public Invidious instance
        invidious_url = f"https://invidious.io/api/v1/videos/{video_id}"
        
        try:
            import urllib.request
            import json
            
            req = urllib.request.Request(invidious_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; VideoDownloader/1.0)')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                return {
                    'type': 'video',
                    'title': data.get('title', 'Unknown Title'),
                    'uploader': data.get('author', 'Unknown'),
                    'duration': self.format_duration(data.get('lengthSeconds')),
                    'view_count': data.get('viewCount', 0),
                    'formats': self.parse_invidious_formats(data.get('formatStreams', [])),
                    'url': url
                }
        except Exception as e:
            logger.warning(f"Invidious extraction failed: {e}")
            return None

    def parse_invidious_formats(self, streams):
        """Parse Invidious format streams"""
        formats = []
        for stream in streams:
            if stream.get('container') in ['mp4', 'webm']:
                quality = stream.get('quality', 'unknown')
                formats.append({
                    'format_id': stream.get('itag', 'unknown'),
                    'ext': stream.get('container', 'mp4'),
                    'resolution': quality,
                    'url': stream.get('url')
                })
        return formats

    def format_basic_info(self, info, url):
        """Format basic info from flat extraction"""
        if not info:
            return self.create_basic_info(url)
            
        if 'entries' in info:
            return {
                'type': 'playlist',
                'title': info.get('title', 'YouTube Playlist'),
                'uploader': info.get('uploader', 'Unknown'),
                'video_count': len(info.get('entries', [])),
                'videos': [
                    {
                        'title': entry.get('title', 'Video'),
                        'duration': 'Unknown',
                        'url': entry.get('url', ''),
                        'formats': self.get_standard_formats()
                    }
                    for entry in info.get('entries', [])[:10]
                ]
            }
        else:
            return {
                'type': 'video',
                'title': info.get('title', 'YouTube Video'),
                'uploader': info.get('uploader', 'Unknown'),
                'duration': 'Unknown',
                'view_count': 0,
                'formats': self.get_standard_formats(),
                'url': url
            }

    def get_standard_formats(self):
        """Return standard format options when extraction fails"""
        return [
            {'resolution': '1080p', 'format_id': 'mp4'},
            {'resolution': '720p', 'format_id': 'mp4'},
            {'resolution': '480p', 'format_id': 'mp4'},
            {'resolution': '360p', 'format_id': 'mp4'},
        ]

    def extract_age_restricted(self, url):
        """Handle age-restricted videos"""
        try:
            age_opts = self.ydl_opts_info.copy()
            age_opts['age_limit'] = 99
            
            with yt_dlp.YoutubeDL(age_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self.format_video_info(info)
                
        except Exception as e:
            logger.error(f"Age-restricted extraction failed: {str(e)}")
            return self.create_basic_info(url)

    def create_basic_info(self, url):
        """Create basic video info when extraction fails"""
        # Extract video ID from URL for basic info
        video_id = self.extract_video_id(url)
        
        return {
            'type': 'video',
            'title': f'YouTube Video ({video_id})',
            'uploader': 'YouTube',
            'duration': 'Unknown',
            'view_count': 0,
            'formats': [
                {'resolution': '720p', 'format_id': 'mp4'},
                {'resolution': '480p', 'format_id': 'mp4'},
                {'resolution': '360p', 'format_id': 'mp4'},
            ],
            'url': url
        }

    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return 'unknown'

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
                # Anti-bot detection measures
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_skip': ['configs'],
                    }
                },
                # Use different user agent
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
                # Rate limiting
                'sleep_interval': 1,
                'max_sleep_interval': 5,
                'nocheckcertificate': True,
            }
            
    def get_download_url(self, video_url, quality='best', format_type='mp4'):
        """Get direct download URL for the video"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                # Anti-bot detection measures
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_skip': ['configs'],
                    }
                },
                # Use different user agent
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
                # Rate limiting
                'sleep_interval': 1,
                'max_sleep_interval': 5,
                'nocheckcertificate': True,
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
            error_msg = str(e).lower()
            
            if 'sign in to confirm' in error_msg or 'not a bot' in error_msg:
                # Try alternative method
                return self.get_download_url_fallback(video_url, quality, format_type)
            else:
                logger.error(f"Error getting download URL: {str(e)}")
                raise HTTPException(status_code=500, detail="Unable to get download link. Please try again later.")

    def get_download_url_fallback(self, video_url, quality='best', format_type='mp4'):
        """Fallback method for getting download URLs"""
        try:
            # Use youtube-dl style format selection
            fallback_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best/worst',  # Simplified format
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15',
                },
                'sleep_interval': 2,
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                if 'url' in info:
                    return info['url']
                elif 'formats' in info and info['formats']:
                    return info['formats'][-1]['url']
                
                # Last resort - return a generic YouTube URL
                video_id = self.extract_video_id(video_url)
                return f"https://www.youtube.com/watch?v={video_id}"
                
        except Exception as e:
            logger.error(f"Fallback download URL failed: {str(e)}")
            # Return original URL as last resort
            return video_url

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

@app.post("/api/update-ytdlp")
async def update_ytdlp():
    """Update yt-dlp to the latest version"""
    try:
        import subprocess
        import sys
        
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return {"status": "success", "message": "yt-dlp updated successfully"}
        else:
            return {"status": "error", "message": f"Update failed: {result.stderr}"}
            
    except Exception as e:
        return {"status": "error", "message": f"Update failed: {str(e)}"}

@app.get("/api/ytdlp-version")
async def get_ytdlp_version():
    """Get current yt-dlp version"""
    try:
        import yt_dlp
        return {"version": yt_dlp.version.__version__}
    except Exception as e:
        return {"error": str(e)}

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