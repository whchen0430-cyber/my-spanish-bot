import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re
import time

# --- 1. 基礎配置與 PWA 圖示 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""<head><link rel="icon" href="{icon_url}"><link rel="apple-touch-icon" href="{icon_url}"></head>""", unsafe_allow_html=True)
st.set_page_config(page_title="西語全能閱讀 6.0", page_icon="🇪🇸", layout="wide")

if 'study_material' not in st.session_state: st.session_state['study_material'] = None

# --- 2. 配置 Gemini 2.5 Flash 核心 ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 鎖定 2.5 系列對應的型號
    model = genai.GenerativeModel('gemini-2.0-flash-exp') 
except Exception as e:
    st.error(f"❌ 大腦連接失敗：{e}")

# --- 3. 語音生成函數 (加強版) ---
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

# --- 4. 側邊欄：功能設定區 ---
st.sidebar.header("⚙️ 學習設定中心")
if st.sidebar.button("🔔 讀取今日 A2 推播教材"):
    with st.spinner('正在調用今日 A2 任務...'):
        try:
            res = model.generate_content("你是一位專業西語老師。產出一篇 A2 對話教材。格式要求：[SPANISH]原文 [CHINESE]翻譯 [VOCAB]5個重點單字 [GRAMMAR]一個詳細文法解析。用繁體中文。")
            st.session_state['study_material'] = res.text
        except: st.error("API 忙碌中，請等待 30 秒。")

st.sidebar.divider()
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 250, 150)

st.sidebar.subheader("🎙️ 語音語速")
speed_val = st.sidebar.select_slider(
    "選擇語速", options=[-50, -25, -10, 0, 10, 20], value=-25,
    format_func=lambda x: {-50: "極慢 (0.5x)", -25: "舒適 (0.75x)", -10: "略慢 (0.9x)", 0: "正常 (1.0x)", 10: "略快 (1.1x)", 20: "快速 (1.2x)"}.get(x, f"{x}%")
)

mx_female, mx_male = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
es_female, es_male = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"
voice_a, voice_b, voice_main = es_male, es_female, es_female

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", [es_male, mx_male])
    voice_b = st.sidebar.selectbox("角色 B (女)", [es_female, mx_female])
else:
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male])

# --- 5. 工具函數 ---
def format_dialogue(text):
    text = text.replace("**", "")
    processed = re.sub(r'(\s?[^：\s\n]+[:：])', r'\n\n**\1**', text)
    return processed.strip()

def parse_material(raw_text):
    data = {"span": "", "chin": "", "vocab": "", "grammar": ""}
    if not raw_text: return data
    # 清理標籤加粗干擾
    t = raw_text.replace("**[SPANISH]**", "[SPANISH]").replace("**[CHINESE]**", "[CHINESE]").replace("**[VOCAB]**", "[VOCAB]").replace("**[GRAMMAR]**", "[GRAMMAR]")
    span_m = re.search(r'\[SPANISH\](.*?)\[CHINESE\]', t, re.S | re.I)
    chin_m = re.search(r'\[CHINESE\](.*?)\[VOCAB\]', t, re.S | re.I)
    vocab_m = re.search(r'\[VOCAB\](.*?)\[GRAMMAR\]', t, re.S | re.I)
    gram_m = re.search(r'\[GRAMMAR\](.*)', t, re.S | re.I)
    if span_m and chin_m:
        data["span"], data["chin"] = span_m.group(1).strip(), chin_m.group(1).strip()
    if vocab_m and gram_m:
        data["vocab"], data["grammar"] = vocab_m.group(1).strip(), gram_m.group(1).strip()
    return data

# --- 6. 主畫面顯示 ---
st.title("🇪🇸 西語全能閱讀家教 (2.5 Flash)")

topic = st.text_input("輸入練習主題：", key="topic_study", placeholder="例如：在仙台旅遊、西班牙美食...")
if st.button("🚀 生成自訂教材"):
    if not topic: st.warning("請輸入主題！")
    else:
        with st.spinner('正在生成...'):
            try:
                p = f"老師。主題：{topic}。等級：{level}。格式：[SPANISH]原文 [CHINESE]翻譯 [VOCAB]5個單字 [GRAMMAR]詳細文法。繁中輸出。"
                res = model.generate_content(p)
                st.session_state['study_material'] = res.text
            except: st.error("API 目前忙碌，請等 30 秒再試。")

if st.session_state['study_material']:
    parsed = parse_material(st.session_state['study_material'])
    if parsed["span"]:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🇪🇸 原文")
            st.markdown(format_dialogue(parsed["span"]))
            # 語音合成
            combined_audio = b""
            lines = [l.strip() for l in parsed["span"].split('\n') if l.strip()]
            for line in lines:
                v = voice_a if (format_type == "雙人對話" and ":" in line) else (voice_b if format_type == "雙人對話" else voice_main)
                clean_line = re.sub(r'^.*?[:：]\s*', '', line)
                clip = asyncio.run(get_audio_clip(clean_line, v, speed_val))
                combined_audio += clip
            if combined_audio: st.audio(combined_audio)
        with c2:
            st.subheader("🇹🇼 翻譯")
            st.markdown(format_dialogue(parsed["chin"]))
        
        st.divider()
        t1, t2 = st.tabs(["📌 重點單字", "📖 核心文法詳解"])
        with t1: st.success(parsed["vocab"])
        with t2: st.info(parsed["grammar"])
    else:
        st.error("解析失敗，建議重新生成。")
        with st.expander("原始內容"): st.code(st.session_state['study_material'])
