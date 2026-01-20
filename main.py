import streamlit as st
import cv2
import tempfile
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import google.generativeai as genai
from scenedetect import ContentDetector, SceneManager, open_video
from PIL import Image
from components.video_player import create_synced_video_player

# Config
st.set_page_config(page_title="Binumi AI Video Tagger", layout="wide")

# History file
HISTORY_FILE = Path("analysis_history.json")

def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
    return []

def save_to_history(video_name, results):
    history = load_history()
    history.insert(0, {
        "id": len(history) + 1,
        "video_name": video_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "scene_count": len(results),
        "results": results
    })
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

def clean_json_string(s):
    if "```json" in s:
        s = s.split("```json")[1].split("```")[0]
    elif "```" in s:
        s = s.split("```")[1].split("```")[0]
    return s.strip()

def detect_scenes(video_path):
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0))
    sm.detect_scenes(video=video)
    return sm.get_scene_list()

def extract_frame(video_path, time_ms):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, time_ms)
    ret, frame = cap.read()
    cap.release()
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if ret else None

def analyze_frame(frame):
    model = genai.GenerativeModel('gemini-2.5-flash')
    img = Image.fromarray(frame)
    prompt = 'Analysiere. Gib JSON: {"beschreibung": "max 20 Worte", "tags": ["t1","t2","t3"], "stimmung": "mood"}'
    try:
        resp = model.generate_content([prompt, img])
        return json.loads(clean_json_string(resp.text))
    except Exception as e:
        return {"error": str(e)}

def run_analysis(video_path, video_name):
    """Run the analysis and return results with live preview"""
    progress = st.progress(0)
    status = st.empty()
    
    # Container for live scene cards
    st.markdown("### 🎬 Erkannte Szenen")
    scene_container = st.container()
    
    scenes = detect_scenes(video_path)
    if not scenes:
        cap = cv2.VideoCapture(video_path)
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) * 1000
        scenes = [(pd.Timestamp(0), pd.Timestamp(dur, unit='ms'))]
        cap.release()
    
    status.info(f"📹 {len(scenes)} Szenen erkannt. Analysiere...")
    
    results = []
    for i, scene in enumerate(scenes):
        
        if isinstance(scene[0], pd.Timestamp):
            start, end = 0, scene[1].value / 1e6
        else:
            start, end = scene[0].get_seconds() * 1000, scene[1].get_seconds() * 1000
        
        mid = (start + end) / 2
        frame = extract_frame(video_path, mid)
        
        if frame is not None:
            analysis = analyze_frame(frame)
            if "error" not in analysis:
                tags = analysis.get("tags", [])
                result = {
                    "Scene_ID": i + 1,
                    "Start_Time_s": f"{start/1000:.2f}",
                    "End_Time_s": f"{end/1000:.2f}",
                    "Description": analysis.get("beschreibung", "-"),
                    "Tags": ", ".join(tags) if isinstance(tags, list) else str(tags),
                    "Mood": analysis.get("stimmung", "-")
                }
                results.append(result)
                
                # Live display: Show card immediately
                with scene_container:
                    st.markdown(f"""
                    <div style="border:1px solid #333; border-radius:8px; padding:10px; margin-bottom:8px; background:#1a1a1a;">
                        <span style="color:#888; font-size:0.85em;">Szene {result['Scene_ID']} • {result['Start_Time_s']}s - {result['End_Time_s']}s</span>
                        <div style="margin-top:6px; font-weight:500;">{result['Description']}</div>
                        <div style="margin-top:4px; color:#aaa; font-size:0.9em;">🏷️ {result['Tags']}</div>
                        <div style="color:#888; font-size:0.85em;">😊 {result['Mood']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        import time
        time.sleep(0.5)
        progress.progress((i + 1) / len(scenes))
    
    status.success(f"✅ Fertig! {len(results)} Szenen analysiert.")
    return results

# Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    api_key = st.text_input("Google Gemini API Key", type="password")
    if not api_key:
        try:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key geladen!")
        except:
            pass
    if api_key:
        genai.configure(api_key=api_key)

# Header
st.title("🎬 AI Video Tagging Pipeline")

# Simple state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'video_path' not in st.session_state:
    st.session_state.video_path = None

# Tabs
tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Neue Analyse"])

# Dashboard
with tab1:
    history = load_history()
    if not history:
        st.info("Noch keine Analysen.")
    for h in history:
        with st.expander(f"📹 {h['video_name']} ({h['scene_count']} Szenen)"):
            st.dataframe(pd.DataFrame(h['results']))

# New Analysis
with tab2:
    if not api_key:
        st.warning("⚠️ API Key eingeben!")
    elif st.session_state.results:
        # Show results with synced video player
        st.success(f"✅ {len(st.session_state.results)} Szenen analysiert!")
        
        # Show synced video player if video still exists
        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            create_synced_video_player(st.session_state.video_path, st.session_state.results, height=500)
        else:
            st.dataframe(pd.DataFrame(st.session_state.results))
        
        # Download + New Analysis
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download JSON",
                json.dumps(st.session_state.results, indent=2, ensure_ascii=False),
                "analysis.json", "application/json", use_container_width=True
            )
        with col2:
            if st.button("🔄 Neue Analyse", use_container_width=True):
                st.session_state.results = None
                st.session_state.video_path = None
                st.rerun()
    else:
        # Show uploader
        st.subheader("📁 Video hochladen")
        uploaded = st.file_uploader("Video wählen", type=["mp4", "mov", "avi"])
        
        if uploaded:
            # Save file
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded.read())
            tfile.close()
            video_path = tfile.name
            
            # Layout: Video left, controls right
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.video(video_path)
            
            with col2:
                st.success(f"✅ **{uploaded.name}** bereit")
                
                if st.button("🚀 Analyse starten", type="primary", use_container_width=True):
                    # Save video path to session state so we can show it later
                    st.session_state.video_path = video_path
                    results = run_analysis(video_path, uploaded.name)
                    
                    if results:
                        save_to_history(uploaded.name, results)
                        st.session_state.results = results
                        st.rerun()
                    else:
                        st.error("Keine Ergebnisse.")
