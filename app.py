import streamlit as st
import google.generativeai as genai
import re

# --- 1. 核心設定 ---
st.set_page_config(page_title="西語家教 Elite", page_icon="🇪🇸", layout="centered")

API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. 精簡美化版 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .main { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* 主卡片容器 */
    .content-card {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }
    
    /* 原文與翻譯區塊 */
    .spanish-box {
        background: #f0fdfa;
        border-left: 4px solid #0d9488;
        padding: 12px;
        border-radius: 8px;
        font-size: 1.1rem;
        line-height: 1.5;
        color: #134e4a;
        margin-bottom: 8px;
    }
    .chinese-box {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 10px;
        border-radius: 8px;
        color: #475569;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 15px;
    }

    /* 緊湊筆記區塊：取消大空格，改用細線分界 */
    .note-container {
        border: 1px solid #f1f5f9;
        border-radius: 8px;
        overflow: hidden;
    }
    .note-row {
        display: flex;
        align-items: flex-start;
        padding: 6px 10px;
        border-bottom: 1px solid #f1f5f9;
        background: white;
        font-size: 0.88rem;
        line-height: 1.4;
    }
    .note-row:last-child { border-bottom: none; }
    
    .tag-v { color: #0d9488; font-weight: 700; min-width: 65px; font-size: 0.75rem; margin-top: 2px; }
    .tag-g { color: #f59e0b; font-weight: 700; min-width: 65px; font-size: 0.75rem; margin-top: 2px; }
    
    .note-text { color: #334155; flex: 1; }
    .note-text strong { color: #e11d48; } /* 強調標示 */

    /* 智慧按鈕 */
    .stButton>button {
        border-radius: 8px;
        background: #1e293b;
        color: white;
        font-weight: 600;
        transition: 0.2s;
        height: 3em;
    }
    .stButton>button:hover { background: #000000; transform: translateY(-1px); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音橋接 ---
def st_audio_logic(lines, accent, speed, mode, action):
    clean_lines = [re.sub(r'^.*?[：:]', '', line).replace('**', '').strip() for line in lines]
    js_code = f"""
    <script>
    (function() {{
        const action = "{action}";
        const synth = window.speechSynthesis;
        if (action === "toggle") {{
            if (synth.speaking && !synth.paused) {{ synth.pause(); }}
            else if (synth.paused) {{ synth.resume(); }}
            else {{
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
    st.header("⚙️ 設定")
    if not API_KEY:
        API_KEY = st.text_input("🔑 API Key", type="password")
    accent = st.selectbox("🌍 口音", ["es-ES", "es-MX"])
    speed = st.select_slider("⚡ 語速", options=[0.7, 0.85, 1.0, 1.2], value=1.0)
    st.caption("Model: gemini-flash-latest")

col1, col2 = st.columns([2, 1])
with col1:
    topic = st.text_input("主題", placeholder="例如：銀山溫泉、離岸風電專案...")
with col2:
    level = st.selectbox("等級", ["A1", "A2", "B1", "B2"], index=1)

mode = st.radio("模式", ["📜 短文", "💬 對話"], horizontal=True)

# --- 5. 生成邏輯 ---
if st.button("✨ 生成教材"):
    if not API_KEY:
        st.warning("請設定 API Key")
    elif not topic:
        st.warning("請輸入主題")
    else:
        try:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel('gemini-flash-latest')
            is_dialogue = "對話" in mode
            final_mode = "dialogue" if is_dialogue else "article"
            style_instr = "兩人對話，格式『名字: 內容』。翻譯也請依照『名字: 內容』分行。" if is_dialogue else "連續短文，禁止名字。"
            
            prompt = f"你是頂尖西語老師。主題：{topic}。等級：{level}。要求：[SPANISH] 200字，形式：{style_instr}。[CHINESE] 對應翻譯並分行。[VOCAB] 5個單字及例句。[GRAMMAR] 2個文法。語音不讀名字。禁止使用 # 號。"
            
            with st.spinner("撰寫中..."):
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
    
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("⏯️ 智慧播放 / 暫停"):
            st_audio_logic(data['SPANISH'].split('\n'), accent, speed, st.session_state['mode'], "toggle")
    with c2:
        if st.button("⏹️ 停止"):
            st_audio_logic([], "", 0, "", "stop")
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    
    # 原文與翻譯
    st.markdown(f'<div class="spanish-box"><b>📖 原文</b><br>{data["SPANISH"].replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chinese-box"><b>🏮 翻譯</b><br>{data["CHINESE"].replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    
    # 緊湊型筆記區
    st.markdown('<div class="note-container">', unsafe_allow_html=True)
    
    # 單字
    for item in data['VOCAB'].split('\n'):
        if item.strip():
            clean_item = item.replace("**", "<strong>").replace("**", "</strong>")
            st.markdown(f'<div class="note-row"><div class="tag-v">VOCAB</div><div class="note-text">{clean_item}</div></div>', unsafe_allow_html=True)
            
    # 文法
    for item in data['GRAMMAR'].split('\n'):
        if item.strip():
            clean_item = item.replace("**", "<strong>").replace("**", "</strong>")
            st.markdown(f'<div class="note-row"><div class="tag-g">GRAMMAR</div><div class="note-text">{clean_item}</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)
