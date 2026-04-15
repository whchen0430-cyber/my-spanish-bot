import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. Android & iOS 圖示配置 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""
    <head>
        <link rel="icon" sizes="192x192" href="{icon_url}">
        <link rel="apple-touch-icon" href="{icon_url}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. 網頁基礎配置 ---
st.set_page_config(page_title="西語全能家教 3.1", page_icon="🇪🇸", layout="wide")

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

# --- 5. 側邊欄設定 (恢復繁體中文介面) ---
st.sidebar.header("⚙️ 系統設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
speed_val = st.sidebar.slider("語速調整 (%)", -50, 20, -10, step=5)

st.sidebar.divider()
st.sidebar.info("💡 測驗模式會產出全西語題目，適合進階練習。")

# --- 6. 主畫面分頁 ---
tab1, tab2 = st.tabs(["📚 今日教材", "📝 挑戰測驗"])

# ----- Tab 1: 今日教材 (繁體中文介面) -----
with tab1:
    st.title("🇪🇸 西語全能一鍵生成家教")
    format_type = st.radio("文章形式", ["一般短文", "雙人對話"], horizontal=True)
    word_count = st.slider("文章總字數", 100, 500, 200)
    topic = st.text_input("想練習的主題？", key="topic_study", placeholder="例如：描述離岸風電計畫...")

    if st.button("🚀 生成精製教材"):
        with st.spinner('正在編排教材...'):
            try:
                style_instruction = "一般短文" if format_type == "一般短文" else "雙人對話標註 A: 與 B:，每句換行"
                prompt = f"""
                請作為專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。
                形式：{style_instruction}。
                
                要求：
                1. 翻譯與筆記必須使用「繁體中文」(Taiwan Traditional Chinese)。
                2. 嚴格遵守輸出格式：
                [SPANISH]
                (西文內容)
                [CHINESE]
                (繁體中文翻譯)
                [NOTES]
                (繁體中文重點筆記)
                """
                response = model.generate_content(prompt)
                full_text = response.text
                
                parts = full_text.split("[CHINESE]")
                spanish_part = parts[0].replace("[SPANISH]", "").strip()
                chinese_part = parts[1].split("[NOTES]")[0].strip()
                notes_part = parts[1].split("[NOTES]")[1].strip()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🇪🇸 西班牙文原文")
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
                    combined_audio = b""
                    lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                    for line in lines:
                        v = "es-ES-AlvaroNeural" if line.startswith("A:") else "es-ES-ElviraNeural"
                        clip = asyncio.run(get_audio_clip(line.replace("A:","").replace("B:",""), v, speed_val))
                        combined_audio += clip
                    if combined_audio: st.audio(combined_audio, format="audio/mp3")

                with col2:
                    st.subheader("🇹🇼 繁體中文翻譯")
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
                st.divider()
                st.success(notes_part)
            except Exception as e:
                st.error(f"錯誤：{e}")

# ----- Tab 2: 挑戰測驗 (測驗題目全西文) -----
with tab2:
    st.title("📝 西語實力檢測站")
    quiz_topic = st.text_input("測驗主題？", key="topic_quiz", placeholder="例如：能源單字練習...")
    
    if st.button("🧠 生成全西語測驗"):
        with st.spinner('正在命題中...'):
            try:
                quiz_prompt = f"""
                請作為專業西語老師，針對「{quiz_topic}」與等級「{level}」設計測驗。
                
                要求：
                1. 測驗內容（題目與選項）必須全部使用「西班牙文」。
                2. 包含 10 題單字選擇題、1 篇 150 字西文短文、5 題閱讀理解選擇題。
                3. 正確答案與說明請使用「繁體中文」。
                
                輸出格式：
                [QUIZ_VOCAB]
                (10題西文單字題)
                [QUIZ_READING]
                (西文短文與5題西文閱讀題)
                [ANSWERS]
                (繁體中文對照答案)
                """
                quiz_response = model.generate_content(quiz_prompt)
                quiz_text = quiz_response.text
                
                try:
                    vocab_q = quiz_text.split("[QUIZ_READING]")[0].replace("[QUIZ_VOCAB]", "").strip()
                    reading_q = quiz_text.split("[ANSWERS]")[0].split("[QUIZ_READING]")[1].strip()
                    answers = quiz_text.split("[ANSWERS]")[1].strip()
                    
                    st.subheader("Parte 1: Vocabulario (單字挑戰)")
                    st.markdown(vocab_q)
                    
                    st.divider()
                    st.subheader("Parte 2: Comprensión de lectura (閱讀理解)")
                    st.markdown(reading_q)
                    
                    st.divider()
                    with st.expander("👉 點擊展開正確答案與解析"):
                        st.info(answers)
                except:
                    st.write(quiz_text) 
            except Exception as e:
                st.error(f"測驗生成失敗：{e}")
