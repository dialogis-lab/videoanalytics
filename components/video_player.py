"""
Custom Video Player Component with Time Tracking
Uses Streamlit's components.html to create a reactive video player
that updates scene cards based on playback position.
"""
import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from pathlib import Path


def create_synced_video_player(video_path: str, scenes: list, height: int = 600):
    """
    Creates a custom HTML5 video player with synchronized scene cards.
    
    Args:
        video_path: Path to the video file
        scenes: List of scene dicts with 'Scene_ID', 'Start_Time_s', 'End_Time_s', 'Description', 'Tags', 'Mood'
        height: Height of the component in pixels
    """
    
    # Read video and encode as base64 for embedding
    with open(video_path, 'rb') as f:
        video_bytes = f.read()
    video_b64 = base64.b64encode(video_bytes).decode()
    
    # Convert scenes to JSON for JavaScript
    scenes_json = json.dumps(scenes, ensure_ascii=False)
    
    # Generate scene cards HTML
    scene_cards_html = ""
    for scene in scenes:
        scene_cards_html += f'''
        <div class="scene-card" 
             data-start="{scene['Start_Time_s']}" 
             data-end="{scene['End_Time_s']}"
             data-scene-id="{scene['Scene_ID']}"
             onclick="seekToScene({scene['Start_Time_s']})">
            <div class="scene-header">
                Szene {scene['Scene_ID']} • {scene['Start_Time_s']}s - {scene['End_Time_s']}s
            </div>
            <div class="scene-description">
                {scene['Description']}
            </div>
            <div class="scene-tags">
                🏷️ {scene['Tags']}
            </div>
            <div class="scene-mood">
                😊 {scene['Mood']}
            </div>
        </div>
        '''
    
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: transparent;
                color: #fff;
            }}
            .container {{
                display: flex;
                gap: 20px;
                height: {height}px;
            }}
            .video-section {{
                flex: 2;
                display: flex;
                flex-direction: column;
            }}
            .scenes-section {{
                flex: 3;
                overflow-y: auto;
                padding-right: 10px;
            }}
            video {{
                width: 100%;
                border-radius: 8px;
                background: #000;
            }}
            .current-time {{
                margin-top: 10px;
                padding: 8px 12px;
                background: #1a1a1a;
                border-radius: 4px;
                font-size: 0.9em;
                color: #888;
            }}
            .scene-card {{
                border: 2px solid #333;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 12px;
                background: #1a1a1a;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            .scene-card:hover {{
                border-color: #555;
                background: #222;
            }}
            .scene-card.active {{
                border-color: #4CAF50;
                background: #1a2d1a;
                box-shadow: 0 0 15px rgba(76, 175, 80, 0.3);
            }}
            .scene-header {{
                color: #888;
                font-size: 0.85em;
                margin-bottom: 8px;
            }}
            .scene-card.active .scene-header {{
                color: #4CAF50;
            }}
            .scene-description {{
                font-weight: 500;
                margin-bottom: 8px;
                line-height: 1.4;
            }}
            .scene-tags {{
                color: #aaa;
                font-size: 0.9em;
                margin-bottom: 4px;
            }}
            .scene-mood {{
                color: #888;
                font-size: 0.85em;
            }}
            .scenes-header {{
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 15px;
                color: #fff;
            }}
            /* Custom scrollbar */
            .scenes-section::-webkit-scrollbar {{
                width: 8px;
            }}
            .scenes-section::-webkit-scrollbar-track {{
                background: #1a1a1a;
                border-radius: 4px;
            }}
            .scenes-section::-webkit-scrollbar-thumb {{
                background: #444;
                border-radius: 4px;
            }}
            .scenes-section::-webkit-scrollbar-thumb:hover {{
                background: #555;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="video-section">
                <video id="videoPlayer" controls>
                    <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div class="current-time" id="timeDisplay">
                    ▶️ 0:00 / Szene: -
                </div>
            </div>
            <div class="scenes-section">
                <div class="scenes-header">📊 {len(scenes)} Szenen</div>
                {scene_cards_html}
            </div>
        </div>
        
        <script>
            const video = document.getElementById('videoPlayer');
            const timeDisplay = document.getElementById('timeDisplay');
            const sceneCards = document.querySelectorAll('.scene-card');
            const scenes = {scenes_json};
            
            function formatTime(seconds) {{
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return mins + ':' + secs.toString().padStart(2, '0');
            }}
            
            function seekToScene(startTime) {{
                video.currentTime = parseFloat(startTime);
                video.play();
            }}
            
            function updateActiveScene() {{
                const currentTime = video.currentTime;
                let activeSceneId = null;
                
                // Find active scene
                for (let scene of scenes) {{
                    const start = parseFloat(scene.Start_Time_s);
                    const end = parseFloat(scene.End_Time_s);
                    if (currentTime >= start && currentTime < end) {{
                        activeSceneId = scene.Scene_ID;
                        break;
                    }}
                }}
                
                // Update UI
                sceneCards.forEach(card => {{
                    const cardSceneId = parseInt(card.dataset.sceneId);
                    if (cardSceneId === activeSceneId) {{
                        card.classList.add('active');
                        // Scroll card into view
                        card.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
                    }} else {{
                        card.classList.remove('active');
                    }}
                }});
                
                // Update time display
                const sceneName = activeSceneId ? 'Szene ' + activeSceneId : '-';
                timeDisplay.innerHTML = '▶️ ' + formatTime(currentTime) + ' / ' + sceneName;
            }}
            
            // Update every 100ms for smooth tracking
            video.addEventListener('timeupdate', updateActiveScene);
            video.addEventListener('seeking', updateActiveScene);
            video.addEventListener('play', updateActiveScene);
        </script>
    </body>
    </html>
    '''
    
    # Render the component
    components.html(html_content, height=height + 50, scrolling=False)
