import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# 1. 配置 Gemini
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # 或使用 gemini-3-flash-preview
except Exception as e:
    st.error(f"❌ 連接失敗：{e}")

# 2. 介面設定
st.set_page_config(page_title="西語全能家教 2.0", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 西語全能家教 2.0：多角色對話版")

# 側邊欄：設定
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
word_count = st.sidebar.slider("文章字數", 100, 500, 200)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
speed = st.sidebar.slider("調整語速 (例如 -25% 是慢速)", -50, 20, 0, step=5)

# 語音選擇
st.sidebar.subheader("語音設定")
if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", ["es-ES-AlvaroNeural", "es-MX-JorgeNeural"])
    voice_b = st.sidebar.selectbox("角色 B (女)", ["es-ES-ElviraNeural", "es-MX-DaliaNeural"])
else:
    voice_main = st.sidebar.selectbox("主要音色", ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"])

# 3. 定義非同步語音生成函數
async def generate_speech(text, voice, rate):
    # rate 格式需為 "+10%" 或 "-20%"
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# 4. 主畫面
topic = st.text_input("想練習的主題？", placeholder="例如：在餐廳點餐、面試對話...")

if st.button("🚀 生成精緻教材"):
    if not topic:
        st.warning("請輸入主題！")
    else:
        with st.spinner('正在編寫精緻教材...'):
            try:
                # 建立更嚴謹的 Prompt
                prompt = f"""
                請作為專業西語老師，針對「{topic}」編寫教材。
                等級：{level}，形式：{format_type}，總字數約 {word_count} 字。
                如果是對話，請用 A: 和 B: 作為每句話的開頭。
                請嚴格遵守格式：
                [SPANISH]
                (文章內容)
                [CHINESE]
                (中文翻譯)
                [NOTES]
                (單字與文法)
                """
                response = model.generate_content(prompt)
                full_text = response.text
                
                # 解析內容
                spanish_part = full_text.split("[CHINESE]")[0].replace("[SPANISH]", "").strip()
                chinese_part = full_text.split("[CHINESE]")[1].split("[NOTES]")[0].strip()
                notes_part = full_text.split("[NOTES]")[1].strip()

                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🇪🇸 西班牙文原文")
                    # 精緻化編排：讓對話變粗體
                    display_text = re.sub(r'([AB]:)', r'**\1**', spanish_part)
                    st.markdown(display_text)
                    
                    # 語音處理
                    if format_type == "雙人對話":
                        # 拆解對話內容來生成不同聲音
                        lines = spanish_part.split('\n')
                        for line in lines:
                            if line.startswith("A:"):
                                st.write("👤 角色 A：")
                                audio = asyncio.run(generate_speech(line.replace("A:", ""), voice_a, speed))
                                st.audio(audio, format="audio/mp3")
                            elif line.startswith("B:"):
                                st.write("👩 角色 B：")
                                audio = asyncio.run(generate_speech(line.replace("B:", ""), voice_b, speed))
                                st.audio(audio, format="audio/mp3")
                    else:
                        audio = asyncio.run(generate_speech(spanish_part, voice_main, speed))
                        st.audio(audio, format="audio/mp3")

                with col2:
                    st.subheader("🇹🇼 中文對照")
                    st.markdown(re.sub(r'([AB]:)', r'**\1**', chinese_part))
                
                st.divider()
                st.subheader("📝 重點筆記")
                st.success(notes_part)
                
            except Exception as e:
                st.error(f"錯誤：{e}")
