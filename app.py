import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. 圖示與基礎配置 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""<head><link rel="icon" href="{icon_url}"><link rel="apple-touch-icon" href="{icon_url}"></head>""", unsafe_allow_html=True)
st.set_page_config(page_title="西語全能家教 3.8", page_icon="🇪🇸", layout="wide")

# --- 2. 初始化會話狀態 (核心解決方案) ---
if 'study_material' not in st.session_state:
    st.session_state['study_material'] = None  # 儲存教材內容
if 'my_notes' not in st.session_state:
    st.session_state['my_notes'] = []         # 儲存自訂單字筆記
if 'quiz_content' not in st.session_state:
    st.session_state['quiz_content'] = None    # 儲存測驗內容

# --- 3. 配置 Gemini 3 Flash Preview ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
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

# --- 5. 側邊欄設定 ---
st.sidebar.header("⚙️ 設定中心")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)
speed_val = st.sidebar.select_slider("語速選擇", options=[-50, -25, -10, 0, 10, 20], value=-25, format_func=lambda x: f"{x}%")

mx_female, mx_male = "es-MX-DaliaNeural", "es-MX-JorgeNeural"
es_female, es_male = "es-ES-ElviraNeural", "es-ES-AlvaroNeural"

if format_type == "雙人對話":
    voice_a, voice_b = es_male, es_female
else:
    voice_main = es_female

# --- 6. 主畫面分頁 ---
tab1, tab2, tab3 = st.tabs(["📚 今日教材", "📝 挑戰測驗", "📓 智能筆記本"])

# ----- Tab 1: 今日教材 -----
with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習的主題？", key="topic_study")

    if st.button("🚀 生成精製教材"):
        with st.spinner('正在編排教材...'):
            prompt = f"專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。形式：{format_type}。格式：[SPANISH]原文[CHINESE]繁中翻譯[NOTES]繁中筆記"
            response = model.generate_content(prompt)
            # 將結果存入 session_state，避免消失
            st.session_state['study_material'] = response.text

    # 只要 session_state 有內容，就顯示出來
    if st.session_state['study_material']:
        full_text = st.session_state['study_material']
        try:
            spanish_part = full_text.split("[CHINESE]")[0].replace("[SPANISH]", "").strip()
            chinese_part = full_text.split("[CHINESE]")[1].split("[NOTES]")[0].strip()
            notes_part = full_text.split("[NOTES]")[1].strip()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🇪🇸 西班牙文原文")
                st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
                # 語音
                combined_audio = b""
                lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                for line in lines:
                    v = voice_a if (format_type == "雙人對話" and line.startswith("A:")) else (voice_b if (format_type == "雙人對話" and line.startswith("B:")) else (voice_main if format_type == "一般短文" else voice_a))
                    clip = asyncio.run(get_audio_clip(line.replace("A:","").replace("B:",""), v, speed_val))
                    combined_audio += clip
                if combined_audio: st.audio(combined_audio, format="audio/mp3")
            with col2:
                st.subheader("🇹🇼 繁體中文翻譯")
                st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
            st.divider()
            st.success(f"💡 重點筆記：\n\n{notes_part}")
        except: st.error("內容解析錯誤，請重新生成。")

# ----- Tab 2: 挑戰測驗 -----
with tab2:
    st.title("📝 西語實力檢測站")
    quiz_topic = st.text_input("測驗主題？", key="quiz_input")
    if st.button("🧠 生成全西語測驗"):
        with st.spinner('命題中...'):
            quiz_prompt = f"針對主題「{quiz_topic}」與等級「{level}」設計全西語測驗。格式：[QUIZ_VOCAB][QUIZ_READING][ANSWERS]"
            q_res = model.generate_content(quiz_prompt)
            st.session_state['quiz_content'] = q_res.text

    if st.session_state['quiz_content']:
        st.write(st.session_state['quiz_content'])

# ----- Tab 3: 智能筆記本 -----
with tab3:
    st.title("📓 我的智能動態筆記本")
    c_word = st.text_input("輸入文章中不懂的單字：", key="c_word_input")
    
    if st.button("🔍 加入筆記區並解析"):
        if c_word:
            with st.spinner(f'正在解析 {c_word}...'):
                word_prompt = f"請針對西班牙文單字「{c_word}」提供繁體中文解釋、詞性與兩個例句。"
                w_res = model.generate_content(word_prompt)
                st.session_state['my_notes'].insert(0, {"word": c_word, "content": w_res.text})
    
    st.divider()
    if st.session_state['my_notes']:
        if st.button("🗑️ 清空筆記"):
            st.session_state['my_notes'] = []
            st.rerun()
        for n in st.session_state['my_notes']:
            with st.expander(f"📌 {n['word']}", expanded=True):
                st.write(n['content'])
