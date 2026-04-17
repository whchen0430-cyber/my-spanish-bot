import streamlit as st
import google.generativeai as genai
import re

# --- 1. 核心設定 ---
st.set_page_config(page_title="西語家教 Elite", page_icon="🇪🇸", layout="centered")

# 優先讀取 Secrets 中的 API KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. UI 質感美化 CSS (維持您的頂級美化結構) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .main { background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); font-family: 'Inter', sans-serif; }
    
    .content-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    .spanish-box {
        background: linear-gradient(to right, #ffffff, #f0fdfa);
        border-left: 6px solid #0d9488;
        padding: 18px;
        border-radius: 12px;
        font-size: 1.15rem;
        line-height: 1.6;
        color: #134e4a;
        margin-bottom: 12px;
    }
    
    .chinese-box {
        background: linear-gradient(to right, #ffffff, #fffbeb);
        border-left: 6px solid #f59e0b;
        padding: 15px;
        border-radius: 12px;
        color: #475569;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 20px;
    }

    .note-item {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 15px;
        margin-bottom: 8px;
        transition: all 0.2s;
        display: flex;
        align-items: center;
    }
    .note-item:hover {
        border-color: #0d9488;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transform: translateX(4px);
    }
    .note-tag {
        background: #0d9488;
        color: white;
        font-size: 0.7rem;
        font-weight: 800;
        padding: 2px 8px;
        border-radius: 20px;
        margin-right: 12px;
        text-transform: uppercase;
    }
    .note-content { font-size: 0.9rem; color: #334155; }
    .note-content strong { color: #be123c; }

    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: white;
        height: 3.5em;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { background: #000000; transform: translateY(-2px); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音橋接 (單鍵 Toggle 邏輯) ---
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
                    if ("{mode}" === "dialogue") {{ utterance.pitch = (idx % 2 === 0) ? 0.85 : 1.15; }}
                    utterance.onend = () => {{ idx++; setTimeout(play, 300); }};
                    synth.speak(utterance);
                }}
                play();
            }}
        }} else if (action === "stop") {{ synth.cancel(); }}
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --- 4. 主介面 UI ---
st.title("🇪🇸 西語家教 Elite")

with st.sidebar:
    st.header("⚙️ Settings")
    if not API_KEY:
        API_KEY = st.text_input("🔑 API Key", type="password")
    accent = st.selectbox("🌍 Accent", ["es-ES", "es-MX"])
    speed = st.select_slider("⚡ Speed", options=[0.7, 0.85, 1.0, 1.2], value=1.0)
    st.divider()
    st.caption("Model: gemini-flash-latest")

col1, col2 = st.columns([2, 1])
with col1:
    topic = st.text_input("Topic", placeholder="例如：討論離岸風電計畫、銀山溫泉、alphabet教材...")
with col2:
    level = st.selectbox("Level", ["A1", "A2", "B1", "B2"], index=1)

mode = st.radio("Mode", ["📜 短文 (Article)", "💬 對話 (Dialogue)"], horizontal=True)

# --- 5. 生成邏輯 ---
if st.button("✨ 生成優質教材"):
    if not API_KEY:
        st.warning("Please set API Key")
    elif not topic:
        st.warning("Please enter a topic")
    else:
        try:
            genai.configure(api_key=API_KEY)
            # 依據要求更改為最新 Flash 模型
            model = genai.GenerativeModel('gemini-flash-latest')
            is_dialogue = "對話" in mode
            final_mode = "dialogue" if is_dialogue else "article"
            
            style_instr = "兩人對話，格式『名字: 內容』。中文翻譯也請依照『名字: 內容』分行。" if is_dialogue else "連續短文，禁止名字。"
            
            prompt = f"你是頂尖西語老師。主題：{topic}。等級：{level}。要求：[SPANISH] 200字左右，形式：{style_instr}。[CHINESE] 對應翻譯，若為對話必須分行。[VOCAB] 5個單字及例句。[GRAMMAR] 2個重要文法。語音不讀名字。禁止使用 # 或 ###。"
            
            with st.spinner("Gemini 正在全速編排教材..."):
                response = model.generate_content(prompt)
                full_text = response.text.replace('###', '').replace('#', '')
                sections = re.split(r'\[(SPANISH|CHINESE|VOCAB|GRAMMAR)\]', full_text)
                if len(sections) >= 9:
                    st.session_state['data'] = {sections[i]: sections[i+1].strip() for i in range(1, len(sections), 2)}
                    st.session_state['mode'] = final_mode
        except Exception as e:
            st.error(f"Error: {e}")

# --- 6. 結果呈現 ---
if 'data' in st.session_state:
    data = st.session_state['data']
    
    # 智慧播放控制按鈕
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("⏯️ 智慧播放 / 暫停 / 繼續"):
            st_audio_logic(data['SPANISH'].split('\n'), accent, speed, st.session_state['mode'], "toggle")
    with c2:
        if st.button("⏹️ 停止重置"):
            st_audio_logic([], "", 0, "", "stop")
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    
    # 原文與翻譯 (加入分行處理)
    st.markdown(f'<div class="spanish-box"><b>📖 Original</b><br>{data["SPANISH"].replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chinese-box"><b>🏮 Traducción</b><br>{data["CHINESE"].replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    
    st.write("✨ **Study Notes**")
    
    # 單字卡片
    for item in data['VOCAB'].split('\n'):
        if item.strip():
            st.markdown(f'<div class="note-item"><span class="note-tag">VOCAB</span><span class="note-content">{item.replace("**", "<strong>").replace("**", "</strong>")}</div>', unsafe_allow_html=True)
            
    # 文法卡片
    for item in data['GRAMMAR'].split('\n'):
        if item.strip():
            st.markdown(f'<div class="note-item" style="border-color: #f59e0b;"><span class="note-tag" style="background: #f59e0b;">GRAMMAR</span><span class="note-content">{item.replace("**", "<strong>").replace("**", "</strong>")}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
