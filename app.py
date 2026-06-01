import streamlit as st
import google.generativeai as genai
import re

# --- 1. 核心設定 ---
st.set_page_config(page_title="西語智慧家教 Elite", page_icon="🇪🇸", layout="centered")

# 建議在 Streamlit Secrets 中設定 GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. 旗艦卡片美學與排版 CSS ---
# 順應你的喜好：單字 strong 僅使用橘紅色純粗體，移除任何黃色螢光底色，畫面極致乾淨。
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .main { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    .content-card {
        background: white; border-radius: 16px; padding: 25px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); border: 1px solid #e2e8f0;
        margin-top: 20px;
    }
    .text-block {
        padding: 18px; border-radius: 12px; margin-bottom: 16px;
        font-size: 1.05rem; line-height: 1.8;
    }
    .spanish-theme { background: #f0fdf4; border-left: 6px solid #22c55e; color: #0f172a; font-weight: 500; }
    .chinese-theme { background: #fefce8; border-left: 6px solid #eab308; color: #334155; font-style: italic; }
    .note-container { border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; margin-top: 15px; }
    .note-row { display: flex; align-items: flex-start; padding: 12px 16px; border-bottom: 1px solid #f1f5f9; background: white; font-size: 0.95rem; }
    .note-row:last-child { border-bottom: none; }
    .tag-v { color: #f87171; font-weight: 700; min-width: 100px; font-size: 0.8rem; letter-spacing: 0.5px; }
    .tag-g { color: #64748b; font-weight: 700; min-width: 100px; font-size: 0.8rem; letter-spacing: 0.5px; }
    .note-text { flex: 1; color: #334155; }
    
    /* 重點單字優化：純粗體，無螢光底色 */
    strong { font-weight: 700; color: #c2410c; background-color: transparent; padding: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音合成橋接 (雙角色音調與純淨化) ---
def st_audio_logic(lines, accent, speed, character):
    # 雙重清洗：徹底拔除 Markdown 的星號，讓語音發音絕無雜音
    clean_lines = [re.sub(r'^.*?[：:]', '', line).replace('**', '').replace('*', '').strip() for line in lines if line.strip()]
    
    # 根據角色切換音調 (Pitch)
    pitch = 0.85 if character == "A" else 1.25
    
    js_code = f"""
    <script>
    (function() {{
        const synth = window.speechSynthesis;
        synth.cancel(); // 播放前先清空，防止重疊
        
        const lines = {clean_lines};
        let idx = 0;
        
        function play() {{
            if (idx >= lines.length) return;
            const utterance = new SpeechSynthesisUtterance(lines[idx]);
            utterance.lang = "{accent}";
            utterance.rate = {speed};
            utterance.pitch = {pitch};
            
            // 智慧尋找對應口音的內建語音包
            const voices = synth.getVoices();
            const matchedVoice = voices.find(v => v.lang.includes("{accent}"));
            if (matchedVoice) {{ utterance.voice = matchedVoice; }}
            
            utterance.onend = () => {{ idx++; setTimeout(play, 200); }};
            synth.speak(utterance);
        }}
        play();
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --- 4. 主介面排版 ---
st.title("🇪🇸 西語智慧家教 Elite (Streamlit 旗艦版)")
st.caption("250字黃金精華教材 • 多國口音智慧切換")

with st.sidebar:
    st.header("⚙️ 學習設定")
    topic_input = st.text_input("輸入你想演練的主題：", value="在馬德里小酒館與多年未見的老朋友重逢，一起乾杯慶祝並分享未來的計畫")
    
    accent = st.selectbox("選擇發音口音：", [
        ("es-ES", "🇪🇸 西班牙本土 (Castellano)"),
        ("es-MX", "🇲🇽 墨西哥 (Mexicano)"),
        ("es-US", "🇺🇸 美國地區西語"),
        ("es-AR", "🇦🇷 阿根廷 (Rioplatense)")
    ], format_func=lambda x: x[1])[0]
    
    speed = st.slider("調整老師語速：", min_value=0.5, max_value=1.5, value=0.9, step=0.1)

# --- 5. AI 生成邏輯 ---
if st.button("🪄 生成客製化實戰教材", use_container_width=True):
    if not API_KEY:
        st.error("請在 st.secrets 中設定您的 GEMINI_API_KEY")
    else:
        genai.configure(api_key=API_KEY)
        # 使用你最熟悉的穩定旗艦模型
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        你是最溫柔、專業的西班牙語老師。請針對主題「{topic_input}」，為 A2-B1 等級的學生設計一份實用教材。
        請嚴格遵守以下格式規範，不要自創額外的標籤，總字數必須剛好固定在 250 字左右：

        [SPANISH]
        這裡寫西班牙文小短文或雙人對話（如果是對話，請明確寫出角色名字如 Juan:, Maria:）。
        請將需要學生注意的「重要單字或片語」用 Markdown 的粗體標籤 ** 包裹起來，例如：**reencuentro**。

        [CHINESE]
        這裡寫整篇西班牙文的「繁體中文」翻譯。

        [VOCAB]
        列出短文中被加粗的重要單字，格式為：**單字** (中文解釋)。每個單字換行。

        [GRAMMAR]
        列出 1-2 個實用的文法或句型重點解析。
        """
        
        with st.spinner("⏳ 老師正在為您精心雕刻 250 字卡片教材..."):
            try:
                response = model.generate_content(prompt)
                text = response.text
                
                # 精準切分區塊
                if "[SPANISH]" in text and "[CHINESE]" in text and "[VOCAB]" in text and "[GRAMMAR]" in text:
                    parts = text.split("[SPANISH]")[1].split("[CHINESE]")
                    spanish_part = parts[0].strip()
                    parts = parts[1].split("[VOCAB]")
                    chinese_part = parts[0].strip()
                    parts = parts[1].split("[GRAMMAR]")
                    vocab_part = parts[0].strip()
                    grammar_part = parts[1].strip()
                    
                    st.session_state['lesson_data'] = {
                        'spanish': spanish_part,
                        'chinese': chinese_part,
                        'vocab': vocab_part,
                        'grammar': grammar_part
                    }
                else:
                    st.error("AI 回傳格式有誤，請再試一次。")
            except Exception as e:
                st.error(f"生成失敗: {e}")

# --- 6. 渲染結果與語音播放 ---
if 'lesson_data' in st.session_state:
    data = st.session_state['lesson_data']
    
    # 語音按鈕列
    col1, col2, col3 = st.columns(3)
    spanish_lines = data['spanish'].split('\n')
    
    with col1:
        if st.button("🗣️ 角色 A 朗讀 (低音調)", use_container_width=True):
            st_audio_logic(spanish_lines, accent, speed, "A")
    with col2:
        if st.button("🗣️ 角色 B 朗讀 (高音調)", use_container_width=True):
            st_audio_logic(spanish_lines, accent, speed, "B")
    with col3:
        if st.button("⏹️ 停止播放", use_container_width=True):
            st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)
            
    # 轉換 Markdown ** 到 HTML <strong>
    def to_html(text):
        html_text = text.replace('\n', '<br>')
        while "**" in html_text:
            html_text = html_text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        return html_text

    # 呈現極致美觀的卡片區塊
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="text-block spanish-theme"><h3>✨ 西文原文 (Texto)</h3>{to_html(data["spanish"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="text-block chinese-theme"><h3>💡 中文翻譯 (Traducción)</h3>{to_html(data["chinese"])}</div>', unsafe_allow_html=True)
    
    # 單字與文法筆記區
    st.markdown('<div class="note-container">', unsafe_allow_html=True)
    
    # 渲染單字
    for vocab_item in data['vocab'].split('\n'):
        if vocab_item.strip():
            st.markdown(f'<div class="note-row"><div class="tag-v">VOCABULARIO</div><div class="note-text">{to_html(vocab_item)}</div></div>', unsafe_allow_html=True)
            
    # 渲染文法
    for grammar_item in data['grammar'].split('\n'):
        if grammar_item.strip():
            st.markdown(f'<div class="note-row"><div class="tag-g">GRAMÁTICA</div><div class="note-text">{to_html(grammar_item)}</div></div>', unsafe_allow_html=True)
            
    st.markdown('</div></div>', unsafe_allow_html=True)
