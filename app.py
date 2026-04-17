import streamlit as st
import google.generativeai as genai
import re
import time

# --- 1. 基礎與模型設定 ---
st.set_page_config(page_title="西語家教 Pro", page_icon="🇪🇸", layout="centered")

# 優先讀取 Secrets 中的 API KEY，若無則留空待手動輸入
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. CSS 極致緊湊排版 ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .spanish-box { background-color: #f0fdfa; border-left: 5px solid #0d9488; padding: 12px; border-radius: 10px; font-size: 1.15rem; line-height: 1.5; margin-bottom: 8px; }
    .chinese-box { background-color: #fefce8; border-left: 5px solid #eab308; padding: 10px; border-radius: 8px; color: #475569; font-size: 0.9rem; margin-bottom: 15px; }
    .list-item { background: white; padding: 5px 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; line-height: 1.4; }
    .list-item strong { color: #f43f5e; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #1e293b; color: white; height: 3.2em; font-weight: bold; border: none; transition: 0.2s; }
    .stButton>button:hover { background-color: #000000; transform: translateY(-1px); }
    div[data-testid="stVerticalBlock"] > div { gap: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. JavaScript 語音橋接 (過濾姓名、自動換聲) ---
def st_speak(lines, accent, speed, mode):
    # 正規表達式：過濾行首的「姓名:」或「姓名：」
    clean_lines = [re.sub(r'^.*?[：:]', '', line).replace('**', '').strip() for line in lines]
    js_code = f"""
    <script>
    (function() {{
        window.speechSynthesis.cancel();
        const lines = {clean_lines};
        let idx = 0;
        function play() {{
            if (idx >= lines.length) return;
            const utterance = new SpeechSynthesisUtterance(lines[idx]);
            utterance.lang = "{accent[:5]}";
            utterance.rate = {speed};
            if ("{mode}" === "dialogue") {{
                // 偶數行低音，奇數行高音，模擬兩個人
                utterance.pitch = (idx % 2 === 0) ? 0.85 : 1.15;
            }}
            utterance.onend = () => {{ idx++; setTimeout(play, 300); }};
            window.speechSynthesis.speak(utterance);
        }}
        play();
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --- 4. 主介面 UI ---
st.title("🇪🇸 西語家教 1.5 Flash")

with st.sidebar:
    st.header("⚙️ 設定中心")
    # 如果 Secrets 沒設，才讓使用者在網頁輸入
    if not API_KEY:
        API_KEY = st.text_input("🔑 輸入 API Key", type="password", help="請輸入您的 Gemini API Key")
    
    accent = st.selectbox("🌍 語音口音", ["es-ES (西班牙)", "es-MX (墨西哥)"], index=0)
    speed = st.select_slider("⚡ 語速", options=[0.7, 0.85, 1.0, 1.2], value=1.0)
    st.divider()
    st.caption("版本：V6.5 旗艦穩定版")

col1, col2 = st.columns([2, 1])
with col1:
    topic = st.text_input("學習主題", placeholder="例如：銀山溫泉辦理入住、討論離岸風電計畫...")
with col2:
    level = st.selectbox("等級", ["A1", "A2", "B1", "B2"], index=1)

mode = st.radio("教材模式", ["📜 一般短文", "💬 雙人對話"], horizontal=True)

# --- 5. 生成邏輯 ---
if st.button("✨ 生成精華教材 (200字)"):
    if not API_KEY:
        st.warning("請先設定 API Key (於側邊欄或 Secrets)")
    elif not topic:
        st.warning("請輸入主題內容")
    else:
        try:
            genai.configure(api_key=API_KEY)
            # 強制使用 1.5-flash 以確保連線穩定與速度
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            final_mode = "dialogue" if "對話" in mode else "article"
            style_instr = "兩人對話，格式『名字: 內容』" if final_mode == "dialogue" else "連續短文，禁止出現名字或冒號。"
            
            prompt = f"你是西語老師。主題：{topic}。等級：{level}。要求：[SPANISH] 固定200字左右，形式：{style_instr}。[CHINESE] 繁體中文翻譯。[VOCAB] 5個單字及例句。[GRAMMAR] 2個文法點。禁止使用 ### 號。語音朗讀時不讀名字。"
            
            with st.spinner("1.5 Flash 正在構思教材..."):
                response = model.generate_content(prompt)
                # 移除 AI 可能產生的 Markdown 標題符號
                full_text = response.text.replace('###', '').replace('#', '')
                
                # 解析標籤區塊
                sections = re.split(r'\[(SPANISH|CHINESE|VOCAB|GRAMMAR)\]', full_text)
                if len(sections) >= 9:
                    content = {sections[i]: sections[i+1].strip() for i in range(1, len(sections), 2)}
                    st.session_state['data'] = content
                    st.session_state['mode'] = final_mode
                else:
                    st.error("AI 格式解析失敗，可能是因為網路波動，請點擊按鈕重試。")
        except Exception as e:
            if "429" in str(e):
                st.error("🚨 連線忙碌中。請『等待一分鐘』不要點擊，讓 API 配額重置。")
            else:
                st.error(f"連線錯誤：{e}")

# --- 6. 結果展現 ---
if 'data' in st.session_state:
    data = st.session_state['data']
    
    # 播放按鈕
    if st.button("▶️ 播放完整語音 (自動換聲且不唸名字)"):
        lines = data['SPANISH'].split('\n')
        st_speak(lines, accent, speed, st.session_state['mode'])
    
    # 呈現區塊
    st.markdown(f'<div class="spanish-box"><b>📖 原文</b><br>{data["SPANISH"].replace("**", "<b>").replace("**", "</b>").replace("\\n", "<br>")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chinese-box"><b>🏮 翻譯</b><br>{data["CHINESE"]}</div>', unsafe_allow_html=True)
    
    st.write("---")
    st.caption("💡 單字與文法解析 (緊湊版)")
    
    # 將單字與文法解析合併呈現，省去標題空間
    full_notes = data['VOCAB'].split('\n') + data['GRAMMAR'].split('\n')
    for item in full_notes:
        if item.strip():
            st.markdown(f'<div class="list-item">{item.replace("**", "<strong>").replace("**", "</strong>")}</div>', unsafe_allow_html=True)
