import streamlit as st
from gtts import gTTS
from pydub import AudioSegment
import google.generativeai as genai
import io

# 1. 讀取保險箱裡的 API Key
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

# 2. 網頁介面設定
st.set_page_config(page_title="西語一鍵生成", page_icon="🇪🇸")
st.title("🇪🇸 西語自動化學習機器人")

# 側邊欄：設定選項
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
word_count = st.sidebar.slider("文章大約字數", 50, 400, 150)
speed = st.sidebar.slider("調整語速 (0.7 最適中)", 0.5, 1.0, 0.7)

# 主畫面：輸入主題
topic = st.text_input("想練習什麼主題？", placeholder="例如：在超市買水果、描述我的周末...")

if st.button("🚀 生成文章與音檔"):
    if not topic:
        st.warning("請輸入一個主題喔！")
    else:
        with st.spinner('Gemini 正在構思文章並錄音...'):
            try:
                # 叫 AI 寫作
                prompt = f"請用西班牙文寫一篇關於 {topic} 的文章，適合 {level} 等級，長度約 {word_count} 字。內容要實用。請只給出西班牙文內容，不要附帶翻譯或解釋。"
                response = model.generate_content(prompt)
                spanish_text = response.text
                
                # 顯示文章
                st.success(f"✅ 已生成適合 {level} 的文章！")
                st.text_area("文章內容：", value=spanish_text, height=250)
                
                # 轉成語音 (gTTS)
                tts = gTTS(text=spanish_text, lang='es')
                mp3_fp = io.BytesIO()
                tts.write_to_fp(mp3_fp)
                mp3_fp.seek(0)
                
                # 調整語速 (pydub)
                audio = AudioSegment.from_file(mp3_fp, format="mp3")
                new_sample_rate = int(audio.frame_rate * speed)
                final_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
                final_audio = final_audio.set_frame_rate(audio.frame_rate)
                
                # 輸出音檔
                out_fp = io.BytesIO()
                final_audio.export(out_fp, format="mp3")
                
                st.audio(out_fp)
                st.download_button("📥 下載此音檔 (MP3)", out_fp, file_name=f"spanish_{topic}.mp3")
                
            except Exception as e:
                st.error(f"發生錯誤：{e}")
