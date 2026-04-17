import streamlit as st
import google.generativeai as genai
import re

# --- 1. 核心設定 ---
st.set_page_config(page_title="西語家教 Pro", page_icon="🇪🇸", layout="centered")

# 優先讀取 Secrets 中的 API KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. CSS 極致緊湊排版 ---
st.markdown("""
    <style>
    .spanish-box { background-color: #f0fdfa; border-left: 5px solid #0d9488; padding: 12px; border-radius: 10px; font-size: 1.15rem; line-height: 1.5; margin-bottom: 8px; }
    .chinese-box { background-color: #fefce8; border-left: 5px solid #eab308; padding: 10px; border-radius: 8px; color: #475569; font-size: 0.9rem; margin-bottom: 12px; }
    .list-item { background: white; padding: 5px 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; line-height: 1.4; }
    .list-item strong { color: #f43f5e; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1e293b; color: white; height: 3.2em; font-weight: bold; border: none; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.4rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音橋接 (單鍵實現 播放/暫停/繼續) ---
def st_audio_logic(lines, accent, speed, mode, action):
    clean_lines = [re.sub(r'^.*?[：:]', '', line).replace('**', '').strip() for line in lines]
    js_code = f"""
    <script>
    (function() {{
        const action = "{action}";
        const synth = window.speechSynthesis;
        
        if (action === "toggle") {{
            if (synth.speaking && !synth.paused) {{
                synth.pause();
            }} else if (synth.paused) {{
                synth.resume();
            }} else {{
                synth.cancel();
                const lines = {clean_lines};
                let idx = 0;
                function play() {{
                    if (idx >= lines.length) return;
                    const utterance = new SpeechSynthesisUtterance(lines[idx]);
                    utterance.lang = "{accent[:5]}";
                    utterance.rate = {speed};
                    if ("{mode}" === "dialogue") {{
                        utterance.pitch = (idx % 2 === 0) ? 0.85 : 1.15;
                    }}
                    utterance.onend = () => {{ idx++; setTimeout(play, 300); }};
                    synth.speak(utterance);
                }}
                play();
            }}
        }} else if (action === "stop") {{
            synth.cancel();
        }}
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --- 4. 主介面 UI ---
st.title("🇪🇸 西語家教 2.0 Flash")

with st.sidebar:
    st.header("⚙️ 設定中心")
    if not API_KEY:
        API_KEY = st.text_input("🔑 API Key", type="password")
    accent = st.selectbox("🌍 口音", ["es-ES", "es-MX"])
    speed = st.select_slider("⚡ 語速", options=[0.7, 0.85, 1.0, 1.2], value=1.0)

col1, col2 = st.columns([2, 1])
with col1:
    topic = st.text_input("學習主題", placeholder="例如：討論離岸風電計畫、銀山溫泉...")
with col2:
    level = st.selectbox("等級", ["A1", "A2", "B1", "B2"], index=1)

mode = st.radio("模式", ["📜 短文", "💬 對話"], horizontal=True)

# --- 5. 生成邏輯 ---
if st.button("✨ 生成教材 (200字)"):
    if not API_KEY:
        st.warning("請設定 API Key")
    elif not topic:
        st.warning("請輸入主題")
    else:
        try:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel('gemini-flash-latest')
            final_mode = "dialogue" if "對話" in mode else "article"
            style_instr = "兩人對話，格式『名字: 內容』" if final_mode == "dialogue" else "連續短文，禁止名字。"
            prompt = f"你是西語老師。主題：{topic}。等級：{level}。要求：[SPANISH] 200字左右，形式：{style_instr}。[CHINESE] 翻譯。[VOCAB] 5個單字及例句。[GRAMMAR] 2個文法。語音不讀名字。"
            
            with st.spinner("撰寫中..."):
                response = model.generate_content(prompt)
                full_text = response.text.replace('###', '').replace('#', '')
                sections = re.split(r'\[(SPANISH|CHINESE|VOCAB|GRAMMAR)\]', full_text)
                if len(sections) >= 9:
                    st.session_state['data'] = {sections[i]: sections[i+1].strip() for i in range(1, len(sections), 2)}
                    st.session_state['mode'] = final_mode
        except Exception as e:
            st.error(f"錯誤：{e}")

# --- 6. 智慧播放與結果展現 ---
if 'data' in st.session_state:
    data = st.session_state['data']
    
    # 單一智慧控制鍵
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("⏯️ 播放 / 暫停 / 繼續"):
            st_audio_logic(data['SPANISH'].split('\n'), accent, speed, st.session_state['mode'], "toggle")
    with c2:
        if st.button("⏹️ 停止重置"):
            st_audio_logic([], "", 0, "", "stop")
    
    st.markdown(f'<div class="spanish-box"><b>📖 原文</b><br>{data["SPANISH"].replace("**", "<b>").replace("**", "</b>").replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chinese-box"><b>🏮 翻譯</b><br>{data["CHINESE"]}</div>', unsafe_allow_html=True)
    
    st.caption("💡 筆記解析")
    full_notes = data['VOCAB'].split('\n') + data['GRAMMAR'].split('\n')
    for item in full_notes:
        if item.strip():
            st.markdown(f'<div class="list-item">{item.replace("**", "<strong>").replace("**", "</strong>")}</div>', unsafe_allow_html=True)
