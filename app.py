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
st.set_page_config(page_title="西語全能家教 3.6", page_icon="🇪🇸", layout="wide")

# --- 3. 配置 Gemini 3 Flash Preview ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"❌ 大腦連接失敗：{e}")

# --- 4. 語音生成函數 (優化語速處理) ---
async def get_audio_clip(text, voice, rate):
    # edge-tts 的 rate 格式為 "+N%" 或 "-N%"
    # 這裡確保傳入的是帶正負號的字串
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 5. 側邊欄：功能選項整合中心 ---
st.sidebar.header("⚙️ 學習設定中心")

# 基礎教材設定
st.sidebar.subheader("📄 教材參數")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.divider()

# 語音詳細設定 (修正語速標籤與邏輯)
st.sidebar.subheader("🎙️ 語音參數")
# 將 Slider 標籤更換為更直覺的百分比說明
speed_val = st.sidebar.select_slider(
    "語速選擇",
    options=[-50, -25, -10, 0, 10, 20],
    value=-25,
    format_func=lambda x: f"極慢 (0.5x)" if x==-50 else (f"舒適 (0.75x)" if x==-25 else (f"正常 (1.0x)" if x==0 else f"稍快 ({x}%)"))
)

mx_female = "es-MX-DaliaNeural"
mx_male = "es-MX-JorgeNeural"
es_female = "es-ES-ElviraNeural"
es_male = "es-ES-AlvaroNeural"

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男聲)", [es_male, mx_male], format_func=lambda x: "西班牙 (Alvaro)" if "ES" in x else "墨西哥 (Jorge)")
    voice_b = st.sidebar.selectbox("角色 B (女聲)", [es_female, mx_female], format_func=lambda x: "西班牙 (Elvira)" if "ES" in x else "墨西哥 (Dalia)")
else:
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male], 
                                     format_func=lambda x: f"{'西班牙' if 'ES' in x else '墨西哥'} - {'女聲' if 'Dalia' in x or 'Elvira' in x else '男聲'}")

st.sidebar.divider()
st.sidebar.info("💡 語速已修正。建議使用「舒適 (0.75x)」進行初次聽力練習。")

# --- 6. 主畫面分頁 ---
tab1, tab2 = st.tabs(["📚 今日教材", "📝 挑戰測驗"])

# ----- Tab 1: 今日教材 -----
with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習什麼主題？", key="topic_study", placeholder="例如：描述離岸風電計畫...")

    if st.button("🚀 生成精製教材"):
        if not topic:
            st.warning("請先輸入主題喔！")
        else:
            with st.spinner('正在準備教材、翻譯與重點筆記...'):
                try:
                    style_instruction = "一般短文" if format_type == "一般短文" else "雙人對話標註 A: 與 B:，每句必須換行"
                    prompt = f"""
                    請作為專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。
                    形式：{style_instruction}。
                    要求：
                    1. 翻譯與筆記必須使用「繁體中文」(Taiwan Traditional Chinese)。
                    2. 重點筆記 [NOTES] 必須包含：5個重點單字(含西文、繁中解釋及例句)與1個核心文法解說。
                    格式：[SPANISH]原文[CHINESE]繁中翻譯[NOTES]繁中筆記
                    """
                    response = model.generate_content(prompt)
                    full_text = response.text
                    
                    parts_chinese = full_text.split("[CHINESE]")
                    spanish_part = parts_chinese[0].replace("[SPANISH]", "").strip()
                    parts_notes = parts_chinese[1].split("[NOTES]")
                    chinese_part = parts_notes[0].strip()
                    notes_part = parts_notes[1].strip()

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
                    st.subheader("💡 重點單字與文法解說")
                    st.success(notes_part)
                except Exception as e:
                    st.error(f"發生錯誤：{e}")

# ----- Tab 2: 挑戰測驗 -----
with tab2:
    st.title("📝 西語實力檢測站")
    quiz_topic = st.text_input("測驗主題？", key="topic_quiz")
    if st.button("🧠 生成全西語測驗"):
        if not quiz_topic:
            st.warning("請輸入主題！")
        else:
            with st.spinner('正在命題中...'):
                try:
                    quiz_prompt = f"專業西語老師，主題「{quiz_topic}」，等級{level}。題目與選項全西語，答案繁中。含10題單字、1篇短文、5題閱讀。格式：[QUIZ_VOCAB][QUIZ_READING][ANSWERS]"
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
                        with st.expander("👉 查看繁體中文答案解析"):
                            st.info(answers)
                    except: st.write(quiz_text) 
                except Exception as e: st.error(f"失敗：{e}")
