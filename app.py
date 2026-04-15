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
st.set_page_config(page_title="西語全能家教 3.7", page_icon="🇪🇸", layout="wide")

# 初始化 Session State (儲存動態筆記)
if 'my_notes' not in st.session_state:
    st.session_state['my_notes'] = []

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

# --- 5. 側邊欄：設定中心 ---
st.sidebar.header("⚙️ 學習設定中心")
st.sidebar.subheader("📄 教材參數")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.divider()
st.sidebar.subheader("🎙️ 語音參數")
speed_val = st.sidebar.select_slider(
    "語速選擇",
    options=[-50, -25, -10, 0, 10, 20],
    value=-25,
    format_func=lambda x: f"極慢 (0.5x)" if x==-50 else (f"舒適 (0.75x)" if x==-25 else (f"正常 (1.0x)" if x==0 else f"稍快 ({x}%)"))
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
    topic = st.text_input("想練習的主題？", key="topic_study", placeholder="例如：描述離岸風電計畫...")

    if st.button("🚀 生成精製教材"):
        if not topic:
            st.warning("請先輸入主題喔！")
        else:
            with st.spinner('Gemini 3 正在編排教材與重點筆記...'):
                try:
                    style_instruction = "一般短文" if format_type == "一般短文" else "雙人對話標註 A: 與 B:，每句換行"
                    prompt = f"""
                    專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。形式：{style_instruction}。
                    1. 翻譯與筆記必用「繁體中文」。
                    2. [NOTES] 須含 5 個重點單字與 1 個文法解說。
                    格式：[SPANISH]原文[CHINESE]繁中翻譯[NOTES]繁中筆記
                    """
                    response = model.generate_content(prompt)
                    full_text = response.text
                    spanish_part = full_text.split("[CHINESE]")[0].replace("[SPANISH]", "").strip()
                    chinese_part = full_text.split("[CHINESE]")[1].split("[NOTES]")[0].strip()
                    notes_part = full_text.split("[NOTES]")[1].strip()

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("🇪🇸 西班牙文原文")
                        st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
                        combined_audio = b""
                        lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                        for line in lines:
                            v = voice_a if (format_type == "雙人對話" and line.startswith("A:")) else \
                                (voice_b if (format_type == "雙人對話" and line.startswith("B:")) else \
                                (voice_main if format_type == "一般短文" else voice_a))
                            clip = asyncio.run(get_audio_clip(line.replace("A:","").replace("B:",""), v, speed_val))
                            combined_audio += clip
                        if combined_audio: st.audio(combined_audio, format="audio/mp3")
                    with col2:
                        st.subheader("🇹🇼 繁體中文翻譯")
                        st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
                    st.divider()
                    st.success(f"💡 教材重點：\n\n{notes_part}")
                except Exception as e: st.error(f"錯誤：{e}")

# ----- Tab 2: 挑戰測驗 -----
with tab2:
    st.title("📝 西語實力檢測站")
    quiz_topic = st.text_input("測驗主題？", key="topic_quiz")
    if st.button("🧠 生成全西語測驗"):
        if not quiz_topic: st.warning("請輸入主題！")
        else:
            with st.spinner('正在命題中...'):
                try:
                    quiz_prompt = f"專業西語老師，主題「{quiz_topic}」，等級{level}。題目選項全西語，答案繁中。含10題單字、1篇短文、5題閱讀。格式：[QUIZ_VOCAB][QUIZ_READING][ANSWERS]"
                    quiz_response = model.generate_content(quiz_prompt)
                    quiz_text = quiz_response.text
                    try:
                        vocab_q = quiz_text.split("[QUIZ_READING]")[0].replace("[QUIZ_VOCAB]", "").strip()
                        reading_q = quiz_text.split("[ANSWERS]")[0].split("[QUIZ_READING]")[1].strip()
                        answers = quiz_text.split("[ANSWERS]")[1].strip()
                        st.subheader("Parte 1: Vocabulario")
                        st.markdown(vocab_q)
                        st.divider()
                        st.subheader("Parte 2: Comprensión de lectura")
                        st.markdown(reading_q)
                        st.divider()
                        with st.expander("👉 查看答案解析"): st.info(answers)
                    except: st.write(quiz_text) 
                except Exception as e: st.error(f"失敗：{e}")

# ----- Tab 3: 智能筆記本 (新功能) -----
with tab3:
    st.title("📓 我的智能動態筆記本")
    st.info("在閱讀教材時，若有其他想深入了解的單字，請輸入在下方。")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        custom_word = st.text_input("想解析的西班牙文單字：", key="input_custom_word", placeholder="例如：generación")
    
    if custom_word:
        if st.button("🔍 自動生成單字卡"):
            with st.spinner(f'Gemini 3 正在深入解析「{custom_word}」...'):
                word_prompt = f"""
                請針對西班牙文單字「{custom_word}」，根據「{level}」等級提供：
                1. 繁體中文解釋與詞性。
                2. 兩個實用的西班牙文例句（附繁中翻譯）。
                請確保內容精簡且準確。
                """
                word_res = model.generate_content(word_prompt)
                # 存入 Session State
                st.session_state['my_notes'].insert(0, {"word": custom_word, "content": word_res.text})
                # 清空輸入框的邏輯在 Streamlit 較複雜，通常直接顯示結果

    st.divider()
    
    if st.session_state['my_notes']:
        if st.button("🗑️ 清空所有筆記"):
            st.session_state['my_notes'] = []
            st.rerun()
            
        for note in st.session_state['my_notes']:
            with st.expander(f"📌 單字：{note['word']}", expanded=True):
                st.write(note['content'])
    else:
        st.write("目前尚無自訂筆記。")
