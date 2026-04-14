import streamlit as st
from gtts import gTTS
import google.generativeai as genai
import io

# 1. 配置 Gemini (Gemini 3 Flash Preview)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # 使用你在 AI Studio 看到的最新模型名稱
    model = genai.GenerativeModel('gemini-3-flash-preview') 
except Exception as e:
    st.error(f"❌ 大腦連接失敗：請確認 Secrets 內的 API KEY 是否正確。錯誤訊息：{e}")

# 2. 網頁介面設定
st.set_page_config(page_title="西語一鍵家教 (Gemini 3)", page_icon="🇪🇸", layout="wide")
st.title("🇪🇸 西語全能一鍵生成家教 (Gemini 3 Flash)")

# 側邊欄設定
st.sidebar.header("學習設定")
level = st.sidebar.selectbox("西班牙文等級", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
is_slow = st.sidebar.checkbox("使用慢速朗讀 (Slow Mode)", value=True)

# 主畫面
topic = st.text_input("想要練習什麼主題？", placeholder="例如：介紹我的工作、規劃一趟日本旅行")

if st.button("🚀 生成完整教材"):
    if not topic:
        st.warning("請輸入主題喔！")
    else:
        with st.spinner('Gemini 3 正在運用最強大腦編寫教材中...'):
            try:
                # 定義 Prompt (提示詞)
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
                
                # 呼叫 Gemini 3 生成內容
                response = model.generate_content(prompt)
                full_text = response.text
                
                # 解析內容
                try:
                    parts = full_text.split("[CHINESE]")
                    spanish_part = parts[0].replace("[SPANISH]", "").strip()
                    other_parts = parts[1].split("[NOTES]")
                    chinese_part = other_parts[0].strip()
                    notes_part = other_parts[1].strip()
                except:
                    # 容錯機制
                    spanish_part = full_text
                    chinese_part = "解析失敗，請看原文"
                    notes_part = "解析失敗"

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
