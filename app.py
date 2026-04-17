import streamlit as st
import google.generativeai as genai
import re

# --- 1. 核心設定 ---
st.set_page_config(page_title="西語家教 Elite", page_icon="🇪🇸", layout="centered")

API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. UI 質感與對話排版 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .main { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    .content-card {
        background: white; border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
    }
    
    /* 對話/短文 共通樣式 */
    .text-block {
        padding: 12px; border-radius: 8px; margin-bottom: 12px;
        font-size: 1.05rem; line-height: 1.6;
    }
    .spanish-theme { background: #f0fdfa; border-left: 5px solid #0d9488; color: #134e4a; }
    .chinese-theme { background: #fffbeb; border-left: 5px solid #f59e0b; color: #475569; font-size: 0.95rem; }

    /* 強制每一行對話的分界線 */
    .dialogue-line {
        padding-bottom: 6px; margin-bottom: 6px;
        border-bottom: 1px dashed rgba(0,0,0,0.05);
    }
    .dialogue-line:last-child { border-bottom: none; margin-bottom: 0; }

    /* 緊湊筆記區 */
    .note-container { border: 1px solid #f1f5f9; border-radius: 8px; overflow: hidden; margin-top: 10px; }
    .note-row {
        display: flex; align-items: flex-start; padding: 6px 10px;
        border-bottom: 1px solid #f1f5f9; background: white; font-size: 0.88rem;
    }
    .note-row:last-child { border-bottom: none; }
    .tag-v { color: #0d9488; font-weight: 700; min-width: 75px; font-size: 0.75rem; }
    .tag-g { color: #f59e0b; font-weight: 700; min-width: 75px; font-size: 0.75rem; }
    .note-text { flex: 1; color: #334155; }
    .note-text strong { color: #e11d48; }

    .stButton>button { border-radius: 8px; background: #1e293b; color: white; font-weight: 600; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音橋接 ---
def st_audio_logic(lines, accent, speed, mode, action):
    # 清理掉對話中的姓名與標記，只播放純西文
    clean_lines = [re.sub(r'^.*?[：:]', '', line).replace('**', '').strip() for line in lines if line.strip()]
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
    topic = st.text_input("主題", placeholder="例如：銀山溫泉辦理入住...")
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
            
            prompt = f"""你是頂尖西語老師。主題：{topic}。等級：{level}。
            要求格式必須嚴格遵守標籤：
            [SPANISH] 200字左右。若是對話，每句話必須『獨立換行』並標註『名字:』。
            [CHINESE] 對應翻譯。若是對話，每一行翻譯必須與原文對應，且『獨立換行』標註『名字:』。
            [VOCAB] 5個單字及例句。
            [GRAMMAR] 2個文法點。
            語音不讀名字，禁止使用#號。"""
            
            with st.spinner("撰寫中..."):
                response = model.generate_content(prompt)
                res_text = response.text.replace('###', '').replace('#', '')
                sections = re.split(r'\[(SPANISH|CHINESE|VOCAB|GRAMMAR)\]', res_text)
                if len(sections) >= 9:
                    st.session_state['data'] = {sections[i]: sections[i+1].strip() for i in range(1, len(sections), 2)}
                    st.session_state['mode'] = "dialogue" if is_dialogue else "article"
        except Exception as e:
            st.error(f"Error: {e}")

# --- 6. 結果呈現 (核心修復區) ---
if 'data' in st.session_state:
    data = st.session_state['data']
    
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button("⏯️ 播放 / 暫停"):
            st_audio_logic(data['SPANISH'].split('\n'), accent, speed, st.session_state['mode'], "toggle")
    with c2:
        if st.button("⏹️ 停止"):
            st_audio_logic([], "", 0, "", "stop")
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    
    # 原文與翻譯的對話對齊邏輯
    for lang_key, theme in [('SPANISH', 'spanish-theme'), ('CHINESE', 'chinese-theme')]:
        label = "原文" if lang_key == 'SPANISH' else "翻譯"
        # 使用正規表達式切割，確保不論單換行或多換行都視為一筆對話
        lines = [l.strip() for l in re.split(r'\n+', data[lang_key]) if l.strip()]
        
        html_content = f'<div class="text-block {theme}"><b>📖 {label}</b><br>'
        for line in lines:
            html_content += f'<div class="dialogue-line">{line}</div>'
        html_content += '</div>'
        st.markdown(html_content, unsafe_allow_html=True)
    
    # 筆記區
    st.markdown('<div class="note-container">', unsafe_allow_html=True)
    for tag, key, css in [('VOCAB', 'VOCAB', 'tag-v'), ('GRAMMAR', 'GRAMMAR', 'tag-g')]:
        items = [i.strip() for i in data[key].split('\n') if i.strip()]
        for it in items:
            clean_it = it.replace("**", "<strong>").replace("**", "</strong>")
            st.markdown(f'<div class="note-row"><div class="{css}">{tag}</div><div class="note-text">{clean_it}</div></div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
