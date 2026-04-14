import streamlit as st
from gtts import gTTS
import google.generativeai as genai
import io

# 1. 讀取 Secrets 裡的 API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # 使用目前最穩定的 1.5 Flash 最新版本名稱
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    st.error(f"❌ 模型配置出錯：{e}")

# 2. 網頁介面設定
st.set_page_config(page_title="西語全能家教", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 西語全能一鍵生成家教")

# 側邊欄設定
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
is_slow = st.sidebar.checkbox("使用慢速朗讀 (Slow Mode)", value=True)

# 主畫面
topic = st.text_input("想要練習什麼主題？", placeholder="例如：在馬德里點餐、我的週末計畫")

if st.button("🚀 生成完整教材"):
    if not topic:
        st.warning("請輸入主題喔！")
    else:
        with st.spinner('正在為您編寫教材並生成語音中...'):
            try:
                # 定義 Prompt
                prompt = f"""
                請作為一名專業的西班牙語老師，針對主題「{topic}」編寫教材：
                1. 等級：{level}。
                2. 文章：請寫一篇約 150 字的西班牙文短文。
                3. 翻譯：提供該文章的繁體中文翻譯。
                4. 重點：列出 3 個重點單字（含解釋）與 1 個關鍵文法說明。
                
                請嚴格遵守以下格式回報，不要有額外開場白：
                [SPANISH]
                (西班牙文文章)
                [CHINESE]
                (中文翻譯)
                [NOTES]
                (重點單字與文法)
                """
                
                response = model.generate_content(prompt)
                full_text = response.text
                
                # 解析內容
                try:
                    spanish_part = full_text.split("[CHINESE]")[0].replace("[SPANISH]", "").strip()
                    other_part = full_text.split("[CHINESE]")[1]
                    chinese_part = other_part.split("[NOTES]")[0].strip()
                    notes_part = other_part.split("[NOTES]")[1].strip()
                except:
                    # 如果 AI 沒有完全遵守格式，則顯示全文
                    st.warning("格式解析異常，直接顯示生成內容：")
                    st.write(full_text)
                    spanish_part = full_text # 確保語音還能抓到內容

                # --- 顯示結果介面 ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🇪🇸 西班牙文原文")
                    st.info(spanish_part)
                    
                    # 生成音檔
                    tts = gTTS(text=spanish_part, lang='es', slow=is_slow)
                    mp3_fp = io.BytesIO()
                    tts.write_to_fp(mp3_fp)
                    st.audio(mp3_fp)

                with col2:
                    st.subheader("🇹🇼 中文對照翻譯")
                    st.write(chinese_part)
                
                st.divider()
                st.subheader("📝 重點單字與文法解說")
                st.success(notes_part)
                
            except Exception as e:
                st.error(f"發生錯誤：{e}")
