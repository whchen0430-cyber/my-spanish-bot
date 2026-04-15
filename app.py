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
st.set_page_config(page_title="西語全能家教 3.5", page_icon="🇪🇸", layout="wide")

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

# --- 5. 側邊欄：功能選項整合中心 ---
st.sidebar.header("⚙️ 學習設定中心")

# 基礎教材設定
st.sidebar.subheader("📄 教材參數")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"], index=1)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)

st.sidebar.divider()

# 語音詳細設定
st.sidebar.subheader("🎙️ 語音參數")
speed_val = st.sidebar.slider("語速調整 (%)", -50, 20, -10, step=5)

# 音色清單定義
mx_female = "es-MX-DaliaNeural"
mx_male = "es-MX-JorgeNeural"
es_female = "es-ES-ElviraNeural"
es_male = "es-ES-AlvaroNeural"

if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男聲)", [es_male, mx_male], format_func=lambda x: "西班牙 (Alvaro)" if "ES" in x else "墨西哥 (Jorge)")
    voice_b = st.sidebar.selectbox("角色 B (女聲)", [es_female, mx_female], format_func=lambda x: "西班牙 (Elvira)" if "ES" in x else "墨西哥 (Dalia)")
else:
    # 這裡補回了墨西哥音色供一般短文使用
    voice_main = st.sidebar.selectbox("主要音色", [es_female, es_male, mx_female, mx_male], 
                                     format_func=lambda x: f"{'西班牙' if 'ES' in x else '墨西哥'} - {'女聲' if 'Dalia' in x or 'Elvira' in x else '男聲'}")

st.sidebar.divider()
st.sidebar.info("💡 設定完成後，請於右側分頁輸入主題並點擊生成。")

# --- 6. 主畫面分頁 ---
tab1, tab2 = st.tabs(["📚 今日教材", "📝 挑戰測驗"])

# ----- Tab 1: 今日教材 -----
with tab1:
    st.title("🇪🇸 西語全能一鍵家教")
    topic = st.text_input("想練習什麼主題？", key="topic_study", placeholder="例如：討論離岸風電計畫、墨西哥旅遊...")

    if st.button("🚀 生成精製教材"):
        if not topic:
            st.warning("請先輸入主題喔！")
        else:
            with st.spinner('Gemini 3 正在構思教材與重點筆記...'):
                try:
                    style_instruction = "一般短文" if format_type == "一般短文" else "雙人對話並標註 A: 與 B:，每句換行"
                    prompt = f"""
                    請作為專業西語老師。主題：{topic}，等級：{level}，字數：{word_count}。
                    形式：{style_instruction}。
                    
                    要求：
                    1. 翻譯與筆記必須使用「繁體中文」(Taiwan Traditional Chinese)。
                    2. 重點筆記 [NOTES] 必須包含：
                       - 5 個文章重點單字（西文、繁中解釋及例句）。
                       - 1 個核心文法解說。
                    
                    格式規範：
                    [SPANISH]
                    (西文原文內容)
                    [CHINESE]
                    (繁體中文翻譯)
                    [NOTES]
                    (繁體中文單字與文法解說)
                    """
                    response = model.generate_content(prompt)
                    full_text = response.text
                    
                    # 分割內容
                    parts_chinese = full_text.split("[CHINESE]")
                    spanish_part = parts_chinese[0].replace("[SPANISH]", "").strip()
                    parts_notes = parts_chinese[1].split("[NOTES]")
                    chinese_part = parts_notes[0].strip()
                    notes_part = parts_notes[1].strip()

                    col1, col2 = st.columns(2
