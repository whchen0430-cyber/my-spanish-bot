import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# 1. 配置 Gemini 3 Flash
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # 使用 Gemini 3 Flash Preview
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"❌ 連接失敗：{e}")

# 2. 介面設定
st.set_page_config(page_title="西語全能家教 2.0", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 西語全能家教 2.0：Gemini 3 對話版")

# 側邊欄設定
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
word_count = st.sidebar.slider("文章字數", 100, 500, 200)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
speed_val = st.sidebar.slider("語速調整 (%)", -50, 20, -10, step=5) # 預設稍慢

# 語音選擇
st.sidebar.subheader("語音設定")
if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", ["es-ES-AlvaroNeural", "es-MX-JorgeNeural"])
    voice_b = st.sidebar.selectbox("角色 B (女)", ["es-ES-ElviraNeural", "es-MX-DaliaNeural"])
else:
    voice_main = st.sidebar.selectbox("主要音色", ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"])

# 3. 非同步語音生成
async def generate_speech(text, voice, rate):
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# 4. 主畫面
topic = st.text_input("想練習的主題？", placeholder="例如：在馬德里面試、討論綠能發展...")

if st.button("🚀 生成精緻教材"):
    if not topic:
        st.warning("請輸入主題！")
    else:
        with st.spinner('Gemini 3 正在構思精緻教材...'):
            try:
                # 建立 Prompt
                prompt = f"""
                請作為專業西語老師，針對「{topic}」編寫教材。
                等級：{level}，形式：{format_type}，總字數需在 {word_count} 字左右。
                如果是對話，請嚴格使用 A: 和 B: 作為每句話的開頭，並讓對話自然生動。
                請嚴格遵守格式回報：
                [SPANISH]
                (文章內容)
                [CHINESE]
                (中文翻譯)
                [NOTES]
                (列出 5 個重點單字與 1 個核心文法解說)
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
                    # 使用 Markdown 讓 A: B: 變粗體
                    st.markdown(re.sub(r'([AB]:)', r'**\1**', spanish_part))
                    
                    if format_type == "雙人對話":
                        lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                        for line in lines:
                            if line.startswith("A:"):
                                audio = asyncio.run(generate_speech(line.replace("A:", ""), voice_a, speed_val))
                                st.audio(audio, format="audio/mp3")
                            elif line.startswith("B:"):
                                audio = asyncio.run(generate_speech(line.replace("B:", ""), voice_b, speed_val))
                                st.audio(audio, format="audio/mp3")
                    else:
                        audio = asyncio.run(generate_speech(spanish_part, voice_main, speed_val))
                        st.audio(audio, format="audio/mp3")

                with col2:
                    st.subheader("🇹🇼 中文對照翻譯")
                    st.markdown(re.sub(r'([AB]:)', r'**\1**', chinese_part))
                
                st.divider()
                st.subheader("📝 重點筆記")
                st.success(notes_part)
                
            except Exception as e:
                st.error(f"錯誤：{e}")
