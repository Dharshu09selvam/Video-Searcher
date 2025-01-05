from flask import Flask, render_template, request, jsonify, send_file
from googleapiclient.discovery import build
import yt_dlp
import os
import tempfile
import base64

app = Flask(__name__)

# Replace with your actual YouTube API key
API_KEY = 'AIzaSyAFYEg0jSc2eUOh9zW-bZ6k-AQh5RgqO9k'

def get_language_and_region_codes(lang):
    language_region_mappings = {
        'en': ('en', 'US'),
        'english': ('en', 'US'),
        'es': ('es', 'ES'),
        'spanish': ('es', 'ES'),
        'fr': ('fr', 'FR'),
        'french': ('fr', 'FR'),
        'de': ('de', 'DE'),
        'german': ('de', 'DE'),
        'it': ('it', 'IT'),
        'italian': ('it', 'IT'),
        'pt': ('pt', 'PT'),
        'portuguese': ('pt', 'PT'),
        'ru': ('ru', 'RU'),
        'russian': ('ru', 'RU'),
        'ja': ('ja', 'JP'),
        'japanese': ('ja', 'JP'),
        'ko': ('ko', 'KR'),
        'korean': ('ko', 'KR'),
        'hi': ('hi', 'IN'),
        'hindi': ('hi', 'IN')
    }
    return language_region_mappings.get(lang.lower().strip(), ('en', 'US'))

def generate_download_link(video_id):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    download_command = f"yt-dlp {video_url}"
    return download_command

@app.route('/download/<video_id>', methods=['POST'])
def download_video(video_id):
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',  # Download best quality
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        }
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Get video info first
                info = ydl.extract_info(video_url, download=False)
                if info is None:
                    raise Exception("Could not retrieve video information")
                
                filename = ydl.prepare_filename(info)
                
                # Download the video
                ydl.download([video_url])
                
                if not os.path.exists(filename):
                    # If the file doesn't exist with the original extension, try mp4
                    base_filename = os.path.splitext(filename)[0]
                    possible_extensions = ['.mp4', '.webm', '.mkv']
                    for ext in possible_extensions:
                        alt_filename = base_filename + ext
                        if os.path.exists(alt_filename):
                            filename = alt_filename
                            break
                
                if not os.path.exists(filename):
                    raise Exception("Downloaded file not found")
                
                # Send the file to the user
                 
                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=os.path.basename(filename),
                    mimetype='video/mp4'
                )
                
            except Exception as download_error:
                print(f"Download error: {str(download_error)}")
                raise download_error
            
    except Exception as e:
        error_message = f"Download failed: {str(e)}"
        print(error_message)
        return jsonify({'error': error_message}), 500
    finally:
        # Clean up: remove the temporary file
        if 'filename' in locals():
            try:
                os.remove(filename)
            except Exception as cleanup_error:
                print(f"Cleanup error: {str(cleanup_error)}")

@app.route('/', methods=['GET', 'POST'])
def index():
    videos = []
    trending_videos = []
    
    if request.method == 'POST':
        topic = request.form.get('topic')
        language = request.form.get('language', 'en')
        
        lang_code, region_code = get_language_and_region_codes(language)
        
        try:
            youtube = build('youtube', 'v3', developerKey=API_KEY)

            search_request = youtube.search().list(
                q=topic,
                part='snippet',
                type='video',
                maxResults=10,
                relevanceLanguage=lang_code,
                regionCode=region_code,
                safeSearch='moderate'
            )
            search_response = search_request.execute()

            video_ids = [item['id']['videoId'] for item in search_response['items']]
            
            if video_ids:
                stats_request = youtube.videos().list(
                    id=','.join(video_ids),
                    part='statistics,snippet'
                )
                stats_response = stats_request.execute()

                for item in stats_response['items']:
                    video_id = item['id']
                    download_link = generate_download_link(video_id)
                    videos.append({
                        'title': item['snippet']['title'],
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'thumbnail': item['snippet']['thumbnails']['high']['url'],
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'download_link': download_link,
                        'video_id': video_id
                    })

                videos = sorted(videos, key=lambda x: x['like_count'], reverse=True)

                # Trending videos section
                trending_request = youtube.videos().list(
                    chart='mostPopular',
                    part='snippet,statistics',
                    regionCode=region_code,
                    maxResults=5,
                    videoCategoryId='0'
                )
                trending_response = trending_request.execute()

                for item in trending_response['items']:
                    video_id = item['id']
                    download_link = generate_download_link(video_id)
                    trending_videos.append({
                        'title': item['snippet']['title'],
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'thumbnail': item['snippet']['thumbnails']['high']['url'],
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'download_link': download_link,
                        'video_id': video_id
                    })

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            
    return render_template('index.html', videos=videos, trending_videos=trending_videos)

if __name__ == '__main__':
    app.run(debug=True)