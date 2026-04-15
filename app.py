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
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"❌ 連接失敗：{e}")

# 2. 網頁介面設定
st.set_page_config(page_title="西語全能家教 2.2", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 西語全能家教 2.2：精準格式優化版")

# 側邊欄設定
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
word_count = st.sidebar.slider("文章字數", 100, 500, 200)
format_type = st.sidebar.radio("文章形式", ["一般短文", "雙人對話"])
speed_val = st.sidebar.slider("語速調整 (%)", -50, 20, -10, step=5)

# 語音選擇
st.sidebar.subheader("語音設定")
if format_type == "雙人對話":
    voice_a = st.sidebar.selectbox("角色 A (男)", ["es-ES-AlvaroNeural", "es-MX-JorgeNeural"])
    voice_b = st.sidebar.selectbox("角色 B (女)", ["es-ES-ElviraNeural", "es-MX-DaliaNeural"])
else:
    voice_main = st.sidebar.selectbox("主要音色", ["es-ES-ElviraNeural", "es-ES-AlvaroNeural"])

# 3. 語音生成函數
async def get_audio_clip(text, voice, rate):
    rate_str = f"{rate:+d}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# 4. 主畫面
topic = st.text_input("想練習的主題？", placeholder="例如：描述我的日常生活、離岸風電的優點...")

if st.button("🚀 生成精緻教材"):
    if not topic:
        st.warning("請輸入主題！")
    else:
        with st.spinner('正在精準編排教材內容...'):
            try:
                # 這裡加強了對「短文」與「對話」的區分指令
                if format_type == "一般短文":
                    style_instruction = "這必須是一篇描述性的短文，絕對不要出現 A: B: 的對話形式。"
                else:
                    style_instruction = "這必須是兩個人之間的對話。請嚴格使用 A: 和 B: 作為每句話開頭，且 A 與 B 的對話必須換行。"

                prompt = f"""
                請作為專業西語老師，針對「{topic}」編寫教材。
                等級：{level}，字數約 {word_count} 字。
                文章形式：{format_type}。
                指令：{style_instruction}
                
                關於翻譯的嚴格要求：
                1. 中文翻譯必須與西班牙文原文的格式「完全對應」。
                2. 如果原文有 A: 和 B:，中文翻譯也必須在每一句開頭加上 A: 和 B: 並換行。
                
                格式回報：
                [SPANISH]
                (西班牙文內容)
                [CHINESE]
                (中文翻譯內容)
                [NOTES]
                (5個重點單字與1個文法說明)
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
                    # 強制換行與加粗
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
                    
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
                            else: # 防呆：如果沒標 A/B 卻選對話，用預設聲音
                                clip = asyncio.run(get_audio_clip(line, voice_a, speed_val))
                                combined_audio += clip
                        else:
                            clip = asyncio.run(get_audio_clip(line, voice_main, speed_val))
                            combined_audio += clip
                    
                    if combined_audio:
                        st.audio(combined_audio, format="audio/mp3")

                with col2:
                    st.subheader("🇹🇼 中文對照翻譯")
                    # 同樣對中文翻譯進行強制換行處理
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
                
                st.divider()
                st.subheader("📝 重點筆記")
                st.success(notes_part)
                
            except Exception as e:
                st.error(f"錯誤：{e}")
