import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re
import time

# --- 1. 配置與 PWA ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""<head><link rel="icon" href="{icon_url}"><link rel="apple-touch-icon" href="{icon_url}"></head>""", unsafe_allow_html=True)
st.set_page_config(page_title="西語全能家教 6.3", page_icon="🇪🇸", layout="wide")

if 'study_material' not in st.session_state: st.session_state['study_material'] = None
if 'quiz_content' not in st.session_state: st.session_state['quiz_content'] = None

# --- 2. 配置 Gemini 2.0 Flash ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp') 
except Exception as e:
    st.error(f"❌ 大腦連接失敗：{e}")

# --- 3. 語音生成函數 ---
async def get_audio_clip(text, voice, rate):
    clean_text = re.sub(r'[*_#~>]', '', text).strip()
    if not clean_text: return b""
    rate_str = f"{rate:+d}%"
    try:
        communicate = edge_tts.Communicate(clean_text, voice, rate=rate_str)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    except: return b""

# --- 4. 側邊欄：學習設定 (字數功能回歸) ---
st.sidebar.header("⚙️ 學習設定中心")

if st.sidebar.button("🔔 讀取今日 A2 推播教材"):
    with st.spinner('2.0 核心編寫中...'):
        try:
            res = model.generate_content("專業西語老師。產出 A2 對話。格式：[SPANISH]原文 [CHINESE]翻譯 [VOCAB]5單字 [GRAMMAR]詳解。繁中。")
            st.session_state['study_material'] = res.text
        except: st.error("API 忙碌，請等 30 秒。")

st.sidebar.divider()
level = st.sidebar.selectbox("西班牙文等級", ["A1", "A2", "B1", "B2"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])

# --- 字數選擇功能回歸 ---
word_count = st.sidebar.slider("文章目標字數", 100, 500, 200, step=50)

speed_val = st.sidebar.select_slider(
    "語速", options=[-50, -25, -10, 0, 10, 20], value=-25,
    format_func=lambda x: {-50:"0.5x", -25:"0.75x", 0:"1.0x"}.get(x, f"{x}%")
)

# 音色設定
es_f, es_m = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"
mx_f, mx_m = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
v_a, v_b, v_main = es_m, es_f, es_f

if format_type == "雙人對話":
    v_a = st.sidebar.selectbox("角色 A (男)", [es_m, mx_m])
    v_b = st.sidebar.selectbox("角色 B (女)", [es_f, mx_f])
else:
    v_main = st.sidebar.selectbox("主要音色", [es_f, es_m, mx_f, mx_m])

# --- 5. 工具函數 ---
def format_dialogue(text):
    text = text.replace("**", "")
    return re.sub(r'(\s?[^：\s\n]+[:：])', r'\n\n**\1**', text).strip()

def parse_material(raw_text):
    data = {"span": "", "chin": "", "vocab": "", "grammar": ""}
    if not raw_text: return data
    tags = ["SPANISH", "CHINESE", "VOCAB", "GRAMMAR"]
    parts = {}
    for i, tag in enumerate(tags):
        start_pattern = rf"\[{tag}\]"
        end_pattern = rf"\[{tags[i+1]}\]" if i+1 < len(tags) else "$"
        match = re.search(rf"{start_pattern}(.*?){end_pattern}", raw_text, re.S | re.I)
        if match:
            parts[tag.lower()] = match.group(1).strip()
    return {
        "span": parts.get("spanish", ""),
        "chin": parts.get("chinese", ""),
        "vocab": parts.get("vocab", ""),
        "grammar": parts.get("grammar", "")
    }

# --- 6. 主畫面分頁 ---
tab1, tab2 = st.tabs(["📚 教材閱讀訓練", "📝 挑戰測驗區"])

with tab1:
    st.title("🇪🇸 西語 2.0 AI 家教")
    topic = st.text_input("輸入練習主題：", placeholder="例如：仙台旅行、離岸風電...")
    
    if st.button("🚀 生成自訂教材"):
        if not topic: st.warning("請輸入主題")
        else:
            with st.spinner('Gemini 2.0 思考中...'):
                try:
                    # 加入字數指令
                    p = f"老師。主題：{topic}。等級：{level}。文章總長度約 {word_count} 字西文。格式：[SPANISH]原文 [CHINESE]翻譯 [VOCAB]5單字 [GRAMMAR]詳解。繁中輸出。"
                    res = model.generate_content(p)
                    st.session_state['study_material'] = res.text
                except: st.error("伺服器連線忙碌，請重試。")

    if st.session_state['study_material']:
        parsed = parse_material(st.session_state['study_material'])
        if parsed["span"]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🇪🇸 原文")
                st.markdown(format_dialogue(parsed["span"]))
                combined_audio = b""
                lines = [l.strip() for l in parsed["span"].split('\n') if l.strip()]
                for line in lines:
                    v = v_a if (format_type == "雙人對話" and ":" in line) else (v_b if format_type == "雙人對話" else v_main)
                    combined_audio += asyncio.run(get_audio_clip(re.sub(r'^.*?[:：]\s*', '', line), v, speed_val))
                if combined_audio: st.audio(combined_audio)
            with c2:
                st.subheader("🇹🇼 翻譯")
                st.markdown(format_dialogue(parsed["chin"]))
            
            st.divider()
            t_v, t_g = st.tabs(["📌 重點單字", "📖 核心文法詳解"])
            with t_v: st.success(parsed["vocab"])
            with t_g: st.info(parsed["grammar"])

with tab2:
    st.title("📝 實力檢測站")
    q_topic = st.text_input("測驗範圍：", key="q_topic")
    if st.button("🧠 生成全西語測驗"):
        with st.spinner('出題中...'):
            try:
                q_p = f"針對主題「{q_topic}」產出一個{level}等級全西語測驗。含單字選擇、閱讀理解。解析用繁中。標註答案。"
                st.session_state['quiz_content'] = model.generate_content(q_p).text
            except: st.error("API 忙碌")
    if st.session_state['quiz_content']:
        st.write(st.session_state['quiz_content'])
        if st.button("🗑️ 清除"):
            st.session_state['quiz_content'] = None
            st.rerun()
