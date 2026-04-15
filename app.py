import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. 強制更換手機桌面圖示 (黑科技) ---
# 使用 Twemoji 的西班牙國旗圖示，確保加入主畫面時顯示可愛國旗
st.markdown(
    """
    <link rel="apple-touch-icon" href="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/1f1ea-1f1f8.png">
    <link rel="icon" href="https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/1f1ea-1f1f8.png">
    """,
    unsafe_allow_html=True
)

# --- 2. 網頁配置 ---
st.set_page_config(
    page_title="西語全能家教 2.2",
    page_icon="🇪🇸",
    layout="wide"
)

# --- 3. 配置 Gemini 3 Flash Preview (您的專屬模型) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 鎖定您要求的 Gemini 3 Flash Preview 模型
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"❌ 大腦連接失敗，請檢查 Secrets 設定。錯誤：{e}")

# --- 4. 語音生成函數 (支援合併與語速調整) ---
async def get_audio_clip(text, voice, rate):
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# --- 5. 介面標題 ---
st.title("🇪🇸 西語全能一鍵生成家教 (Gemini 3)")
st.caption("專為專業人士打造的自動化學習系統：支援雙人對話、多音色合併與精準格式排版。")

# --- 6. 側邊欄：學習設定 ---
st.sidebar.header("⚙️ 學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
word_count = st.sidebar.slider("文章總字數", 100, 500, 200)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
speed_val = st.sidebar.slider("語速調整 (%)", -50, 20, -10, step=5)

st.sidebar.divider()
st.sidebar.subheader("🎙️ 語音音色設定")
if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", ["es-ES-AlvaroNeural", "es-MX-JorgeNeural"])
    voice_b = st.sidebar.selectbox("角色 B (女)", ["es-ES-ElviraNeural", "es-MX-DaliaNeural"])
else:
    voice_main = st.sidebar.selectbox("主要音色", ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-MX-DaliaNeural"])

# --- 7. 主畫面操作 ---
topic = st.text_input("想練習的主題？", placeholder="例如：討論離岸風電計畫、在馬德里預約餐廳...")

if st.button("🚀 生成精製教材"):
    if not topic:
        st.warning("請輸入主題！")
    else:
        with st.spinner('Gemini 3 正在為您精準編排教材與錄製語音...'):
            try:
                # 強化指令確保格式不走鐘
                if format_type == "一般短文":
                    style_instruction = "這必須是一篇描述性的短文，絕對不要出現 A: B: 的對話形式。"
                else:
                    style_instruction = "這必須是兩個人之間的對話。請嚴格使用 A: 和 B: 作為每句話開頭，且每句對話必須單獨換行。"

                prompt = f"""
                請作為專業西語老師，針對「{topic}」編寫教材。
                等級：{level}，目標字數：約 {word_count} 字。
                形式：{format_type}。
                指令：{style_instruction}
                
                翻譯要求：
                1. 中文翻譯必須與原文格式完全對應。
                2. 如果原文有 A: 和 B:，中文翻譯也必須在每句開頭加上 A: 和 B: 並換行。
                
                輸出格式：
                [SPANISH]
                (西班牙文原文內容)
                [CHINESE]
                (中文翻譯內容)
                [NOTES]
                (5個重點單字含解釋與1個核心文法說明)
                """
                
                response = model.generate_content(prompt)
                full_text = response.text
                
                # 解析內容 (Split)
                spanish_part = full_text.split("[CHINESE]")[0].replace("[SPANISH]", "").strip()
                chinese_part = full_text.split("[CHINESE]")[1].split("[NOTES]")[0].strip()
                notes_part = full_text.split("[NOTES]")[1].strip()

                # --- 渲染畫面 ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🇪🇸 西班牙文原文")
                    # 正規表達式處理：將 A: B: 加粗並強制換行
                    fmt_spanish = re.sub(r'(A:|B:)', r'\n**\1**', spanish_part)
                    st.markdown(fmt_spanish)
                    
                    # 音檔合併處理
                    combined_audio = b""
                    lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                    
                    for line in lines:
                        if format_type == "雙人對話":
                            if line.startswith("A:"):
                                clip = asyncio.run(get_audio_clip(line.replace("A:", ""), voice_a, speed_val))
                                combined_audio += clip
                            elif line.startswith("B:"):
                                clip = asyncio.run(get_audio_clip(line.replace("B:", ""), voice_b, speed_val))
                                combined_audio += clip
                            else:
                                clip = asyncio.run(get_audio_clip(line, voice_a, speed_val))
                                combined_audio += clip
                        else:
                            clip = asyncio.run(get_audio_clip(line, voice_main, speed_val))
                            combined_audio += clip
                    
                    if combined_audio:
                        st.audio(combined_audio, format="audio/mp3")
                        st.download_button("📥 下載完整音檔", combined_audio, file_name=f"spanish_{topic}.mp3")

                with col2:
                    st.subheader("🇹🇼 中文對照翻譯")
                    fmt_chinese = re.sub(r'(A:|B:)', r'\n**\1**', chinese_part)
                    st.markdown(fmt_chinese)
                
                st.divider()
                st.subheader("📝 重點筆記")
                st.success(notes_part)
                
            except Exception as e:
                st.error(f"發生錯誤：{e}")
