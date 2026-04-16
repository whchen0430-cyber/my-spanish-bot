import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. 圖示與配置 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""<head><link rel="icon" href="{icon_url}"><link rel="apple-touch-icon" href="{icon_url}"></head>""", unsafe_allow_html=True)
st.set_page_config(page_title="西語全能家教 4.9", page_icon="🇪🇸", layout="wide")

# 初始化會話狀態
if 'study_material' not in st.session_state: st.session_state['study_material'] = None
if 'my_notes' not in st.session_state: st.session_state['my_notes'] = []
if 'quiz_content' not in st.session_state: st.session_state['quiz_content'] = None

# --- 2. 配置 Gemini 2.5 Flash ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
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

# --- 4. 側邊欄設定 ---
st.sidebar.header("⚙️ 學習設定中心")
if st.sidebar.button("🔔 讀取今日推播教材 (A2)"):
    with st.spinner('正在調用 A2 教材...'):
        try:
            res = model.generate_content("請作為專業西語老師，產出一篇 A2 等級對話教材。要求：翻譯與筆記用繁體中文。標籤格式：[SPANISH]...[CHINESE]...[NOTES]...")
            st.session_state['study_material'] = res.text
        except: st.error("API 忙碌中。")

st.sidebar.divider()
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.subheader("🎙️ 語音設定")

# --- 修正處：加入明確的 format_func 確保顯示人性化標籤 ---
speed_val = st.sidebar.select_slider(
    "語速選擇",
    options=[-50, -25, -10, 0, 10, 20],
    value=-25,
    format_func=lambda x: {
        -50: "極慢 (0.5x)",
        -25: "舒適 (0.75x)",
        -10: "略慢 (0.9x)",
        0: "正常 (1.0x)",
        10: "略快 (1.1x)",
        20: "快速 (1.2x)"
    }.get(x, f"{x}%")
)

mx_female, mx_male = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
es_female, es_male = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", [es_male, mx_male], format_func=lambda x: "西班牙 (Alvaro)" if "ES" in x else "墨西哥 (Jorge)")
    voice_b = st.sidebar.selectbox("角色 B (女)", [es_female, mx_female], format_func=lambda x: "西班牙 (Elvira)" if "ES" in x else "墨西哥 (Dalia)")
else:
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male])

# --- 5. 主分頁 ---
tab1, tab2, tab3 = st.tabs(["📚 今日教材", "📝 挑戰測驗", "📓 智能筆記本"])

def format_dialogue(text):
    text = text.replace("**", "")
    processed = re.sub(r'(\s?[^：\s\n]+[:：])', r'\n\n**\1**', text)
    return processed.strip()

with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習什麼主題？", key="topic_study")
    if st.button("🚀 生成教材"):
        if not topic: st.warning("請輸入主題！")
        else:
            with st.spinner('生成中...'):
                try:
                    p = f"專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。形式：{format_type}。標籤：[SPANISH][CHINESE][NOTES]"
                    res = model.generate_content(p)
                    st.session_state['study_material'] = res.text
                except: st.error("API 忙碌。")

    if st.session_state['study_material']:
        raw = st.session_state['study_material']
        try:
            span_raw = re.search(r'\[SPANISH\](.*?)\[CHINESE\]', raw, re.S).group(1).strip()
            chin_raw = re.search(r'\[CHINESE\](.*?)\[NOTES\]', raw, re.S).group(1).strip()
            note_raw = re.search(r'\[NOTES\](.*)', raw, re.S).group(1).strip()
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🇪🇸 原文")
                st.markdown(format_dialogue(span_raw))
                combined_audio = b""
                lines = [l.strip() for l in span_raw.split('\n') if l.strip()]
                for line in lines:
                    v = voice_a if (format_type == "雙人對話" and ("A:" in line or "1:" in line)) else \
                        (voice_b if (format_type == "雙人對話" and ("B:" in line or "2:" in line)) else voice_main)
                    clean_line = re.sub(r'^.*?[:：]\s*', '', line)
                    clip = asyncio.run(get_audio_clip(clean_line, v, speed_val))
                    combined_audio += clip
                if combined_audio: st.audio(combined_audio, format="audio/mp3")
            with c2:
                st.subheader("🇹🇼 翻譯")
                st.markdown(format_dialogue(chin_raw))
            st.divider()
            st.success(f"💡 筆記：\n\n{note_raw}")
        except: st.error("內容解析失敗，請重新生成。")

with tab3:
    st.title("📓 智能筆記本")
    c_word = st.text_input("輸入單字：", key="c_word")
    if st.button("🔍 解析"):
        if c_word:
            with st.spinner('解析中...'):
                try:
                    w = model.generate_content(f"西語單字「{c_word}」繁中解釋詞性例句。")
                    st.session_state['my_notes'].insert(0, {"word": c_word, "content": w.text})
                except: st.error("解析失敗")
    for n in st.session_state['my_notes']:
        with st.expander(f"📌 {n['word']}", expanded=True): st.write(n['content'])
