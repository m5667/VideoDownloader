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
