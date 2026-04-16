import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. Android & iOS 圖示與 PWA 配置 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""
    <head>
        <link rel="icon" sizes="192x192" href="{icon_url}">
        <link rel="apple-touch-icon" href="{icon_url}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. 網頁基礎配置 ---
st.set_page_config(page_title="西語全能家教 4.5 穩定版", page_icon="🇪🇸", layout="wide")

# 初始化 Session State (鎖定教材與筆記內容)
if 'study_material' not in st.session_state: st.session_state['study_material'] = None
if 'my_notes' not in st.session_state: st.session_state['my_notes'] = []
if 'quiz_content' not in st.session_state: st.session_state['quiz_content'] = None

# --- 3. 配置 Gemini 2.5 Flash (更換為穩定且高配額模型) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 這裡更改為穩定版的 2.5 Flash
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"❌ 大腦連接失敗：{e}")

# --- 4. 語音生成函數 ---
async def get_audio_clip(text, voice, rate):
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 5. 側邊欄：設定中心 ---
st.sidebar.header("⚙️ 學習設定中心")

# 推播功能按鈕 (固定 A2)
if st.sidebar.button("🔔 讀取今日推播教材 (A2)"):
    with st.spinner('正在調用 A2 教材...'):
        try:
            push_prompt = "請作為專業西語老師，產出一篇 A2 等級對話教材。要求：翻譯與筆記用繁體中文。必須嚴格遵守以下標籤格式：[SPANISH]...[CHINESE]...[NOTES]..."
            response = model.generate_content(push_prompt)
            st.session_state['study_material'] = response.text
        except Exception as e:
            st.error(f"暫時無法讀取：{e}")

st.sidebar.divider()
st.sidebar.subheader("📄 教材參數")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.divider()
st.sidebar.subheader("🎙️ 語音設定")
speed_val = st.sidebar.select_slider(
    "語速選擇", options=[-50, -25, -10, 0, 10, 20], value=-25,
    format_func=lambda x: f"舒適 (0.75x)" if x==-25 else (f"正常 (1.0x)" if x==0 else f"{x}%")
)

mx_female, mx_male = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
es_female, es_male = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男聲)", [es_male, mx_male], format_func=lambda x: "西班牙 (Alvaro)" if "ES" in x else "墨西哥 (Jorge)")
    voice_b = st.sidebar.selectbox("角色 B (女聲)", [es_female, mx_female], format_func=lambda x: "西班牙 (Elvira)" if "ES" in x else "墨西哥 (Dalia)")
else:
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male], 
                                     format_func=lambda x: f"{'西班牙' if 'ES' in x else '墨西哥'} - {'女聲' if 'Dalia' in x or 'Elvira' in x else '男聲'}")

# --- 6. 主畫面分頁 ---
tab1, tab2, tab3 = st.tabs(["📚 今日教材", "📝 挑戰測驗", "📓 智能筆記本"])

# ----- Tab 1: 今日教材 -----
with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習什麼主題？", key="topic_study")

    if st.button("🚀 生成自訂教材"):
        if not topic: st.warning("請輸入主題！")
        else:
            with st.spinner('正在編排教材...'):
                try:
                    prompt = f"專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。形式：{format_type}。格式：[SPANISH]原文[CHINESE]繁中翻譯[NOTES]繁中筆記"
                    response = model.generate_content(prompt)
                    st.session_state['study_material'] = response.text
                except Exception as e: st.error(f"連線異常：{e}")

    if st.session_state['study_material']:
        raw_text = st.session_state['study_material']
        # 強化解析邏輯 (Regex)
        try:
            spanish_part = re.search(r'\[SPANISH\](.*?)\[CHINESE\]', raw_text, re.S).group(1).strip()
            chinese_part = re.search(r'\[CHINESE\](.*?)\[NOTES\]', raw_text, re.S).group(1).strip()
            notes_part = re.search(r'\[NOTES\](.*)', raw_text, re.S).group(1).strip()
        except:
            parts = raw_text.replace("[SPANISH]", "").split("[CHINESE]")
            spanish_part = parts[0].strip() if len(parts) > 0 else "解析失敗"
            sub_parts = parts[1].split("[NOTES]") if len(parts) > 1 else ["解析失敗", "解析失敗"]
            chinese_part = sub_parts[0].strip()
            notes_part = sub_parts[1].strip() if len(sub_parts) > 1 else "解析失敗"

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🇪🇸 西班牙文原文")
            st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
            combined_audio = b""
            lines = [l.strip() for l in spanish_part.split('\n') if l.strip()]
            for line in lines:
                if format_type == "雙人對話":
                    v = voice_a if line.startswith("A:") else voice_b
                else:
                    v = voice_main
                clip = asyncio.run(get_audio_clip(line.replace("A:","").replace("B:",""), v, speed_val))
                combined_audio += clip
            if combined_audio: st.audio(combined_audio, format="audio/mp3")

        with col2:
            st.subheader("🇹🇼 繁體中文翻譯")
            st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
        st.divider()
        st.success(f"💡 重點筆記：\n\n{notes_part}")

# ----- Tab 2 & 3 -----
with tab2:
    st.title("📝 實力檢測站")
    quiz_topic = st.text_input("測驗主題？", key="topic_quiz")
    if st.button("🧠 生成測驗"):
        with st.spinner('命題中...'):
            try:
                res = model.generate_content(f"主題{quiz_topic}等級{level}全西語測驗。格式：[QUIZ_VOCAB][QUIZ_READING][ANSWERS]")
                st.session_state['quiz_content'] = res.text
            except: st.error("連線忙碌")
    if st.session_state['quiz_content']: st.write(st.session_state['quiz_content'])

with tab3:
    st.title("📓 智能筆記本")
    c_word = st.text_input("輸入單字：", key="c_word_input")
    if st.button("🔍 解析"):
        if c_word:
            with st.spinner('解析中...'):
                try:
                    w_res = model.generate_content(f"請針對西語單字「{c_word}」提供繁中解釋、詞性與兩個例句。")
                    st.session_state['my_notes'].insert(0, {"word": c_word, "content": w_res.text})
                except: st.error("解析失敗")
    st.divider()
    for n in st.session_state['my_notes']:
        with st.expander(f"📌 {n['word']}", expanded=True): st.write(n['content'])
