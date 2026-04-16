import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. 圖示與配置 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""<head><link rel="icon" href="{icon_url}"><link rel="apple-touch-icon" href="{icon_url}"></head>""", unsafe_allow_html=True)
st.set_page_config(page_title="西語全能家教 5.3", page_icon="🇪🇸", layout="wide")

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
            # 強化指令：要求必須包含文法解析
            res = model.generate_content("你是一位專業西語老師。請產出一篇 A2 等級對話教材。格式：[SPANISH]原文 [CHINESE]翻譯 [NOTES]包含5個單字與1個詳細文法解析。用繁體中文。")
            st.session_state['study_material'] = res.text
        except: st.error("API 忙碌中。")

st.sidebar.divider()
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.subheader("🎙️ 語音設定")
speed_val = st.sidebar.select_slider(
    "語速選擇", options=[-50, -25, -10, 0, 10, 20], value=-25,
    format_func=lambda x: {-50: "極慢 (0.5x)", -25: "舒適 (0.75x)", -10: "略慢 (0.9x)", 0: "正常 (1.0x)", 10: "略快 (1.1x)", 20: "快速 (1.2x)"}.get(x, f"{x}%")
)

mx_female, mx_male = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
es_female, es_male = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"
voice_a, voice_b, voice_main = es_male, es_female, es_female

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", [es_male, mx_male], format_func=lambda x: "西班牙 (Alvaro)" if "ES" in x else "墨西哥 (Jorge)")
    voice_b = st.sidebar.selectbox("角色 B (女)", [es_female, mx_female], format_func=lambda x: "西班牙 (Elvira)" if "ES" in x else "墨西哥 (Dalia)")
else:
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male])

# --- 5. 核心工具函數 ---
def format_dialogue(text):
    text = text.replace("**", "")
    processed = re.sub(r'(\s?[^：\s\n]+[:：])', r'\n\n**\1**', text)
    return processed.strip()

def parse_material(raw_text):
    data = {"span": "", "chin": "", "note": ""}
    if not raw_text: return data
    clean_text = raw_text.replace("**[SPANISH]**", "[SPANISH]").replace("**[CHINESE]**", "[CHINESE]").replace("**[NOTES]**", "[NOTES]")
    span_m = re.search(r'\[SPANISH\](.*?)\[CHINESE\]', clean_text, re.S | re.I)
    chin_m = re.search(r'\[CHINESE\](.*?)\[NOTES\]', clean_text, re.S | re.I)
    note_m = re.search(r'\[NOTES\](.*)', clean_text, re.S | re.I)
    if span_m and chin_m and note_m:
        data["span"], data["chin"], data["note"] = span_m.group(1).strip(), chin_m.group(1).strip(), note_m.group(1).strip()
    return data

# --- 6. 主分頁 ---
tab1, tab2, tab3 = st.tabs(["📚 今日教材", "📝 挑戰測驗", "📓 智能筆記本"])

with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習什麼主題？", key="topic_study")
    if st.button("🚀 生成教材"):
        if not topic: st.warning("請輸入主題！")
        else:
            with st.spinner('正在編排教材...'):
                try:
                    # 強化指令：特別要求「文法解說」
                    p = f"作為老師。主題：{topic}，等級：{level}。格式：[SPANISH]原文 [CHINESE]翻譯 [NOTES]包含5個單字與1個文法解析(Grammar)。用繁體中文。"
                    res = model.generate_content(p)
                    st.session_state['study_material'] = res.text
                except: st.error("API 暫時忙碌。")

    if st.session_state['study_material']:
        parsed = parse_material(st.session_state['study_material'])
        if parsed["span"] and parsed["chin"]:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🇪🇸 原文")
                st.markdown(format_dialogue(parsed["span"]))
                combined_audio = b""
                lines = [l.strip() for l in parsed["span"].split('\n') if l.strip()]
                for line in lines:
                    if format_type == "雙人對話":
                        current_voice = voice_a if any(m in line[:12] for m in ["A:", "1:", "Carlos", "Juan", "Ana"]) else voice_b
                    else:
                        current_voice = voice_main
                    clean_line = re.sub(r'^.*?[:：]\s*', '', line)
                    clip = asyncio.run(get_audio_clip(clean_line, current_voice, speed_val))
                    combined_audio += clip
                if combined_audio: st.audio(combined_audio, format="audio/mp3")
            with c2:
                st.subheader("🇹🇼 翻譯")
                st.markdown(format_dialogue(parsed["chin"]))
            st.divider()
            # 這裡就是顯示文法解析與單字的地方
            st.success(f"💡 重點筆記與文法解析：\n\n{parsed['note']}")
        else:
            st.error("內容解析失敗。")
            with st.expander("原始內容"): st.code(st.session_state['study_material'])

# ----- Tab 3 維持穩定功能 -----
with tab3:
    st.title("📓 智能筆記本")
    c_word = st.text_input("輸入單字：", key="c_word")
    if st.button("🔍 解析"):
        if c_word:
            with st.spinner('解析中...'):
                try:
                    w = model.generate_content(f"針對單字「{c_word}」提供繁中解釋、詞性與兩個例句。")
                    st.session_state['my_notes'].insert(0, {"word": c_word, "content": w.text})
                except: st.error("解析失敗")
    for n in st.session_state['my_notes']:
        with st.expander(f"📌 {n['word']}", expanded=True): st.write(n['content'])
