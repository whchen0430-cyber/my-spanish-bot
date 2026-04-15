import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import io
import re

# --- 1. Android & iOS 圖示黑科技 ---
icon_url = "https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/512x512/1f1ea-1f1f8.png"
st.markdown(f"""
    <head>
        <link rel="icon" sizes="192x192" href="{icon_url}">
        <link rel="apple-touch-icon" href="{icon_url}">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    """, unsafe_allow_html=True)

# --- 2. 網頁基礎配置 ---
st.set_page_config(page_title="西語全能家教 3.0", page_icon="🇪🇸", layout="wide")

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

# --- 5. 側邊欄設定 ---
st.sidebar.header("⚙️ Configuración")
level = st.sidebar.selectbox("Nivel de español", ["A1 初級", "A2 基礎", "B1 中級", "B2 進階"])
speed_val = st.sidebar.slider("Velocidad de voz (%)", -50, 20, -10, step=5)

st.sidebar.divider()
st.sidebar.info("💡 El modo de examen generará automáticamente 10 preguntas de vocabulario y 5 de comprensión de lectura en español.")

# --- 6. 主畫面分頁 ---
tab1, tab2 = st.tabs(["📚 Lección diaria (教材)", "📝 Examen de desafío (測驗)"])

# ----- Tab 1: 今日教材 (保持中文輔助) -----
with tab1:
    st.title("🇪🇸 Tutor de Español con Gemini 3")
    format_type = st.radio("Formato", ["一般短文", "雙人對話"], horizontal=True)
    word_count = st.slider("Número de palabras", 100, 500, 200)
    topic = st.text_input("Tema de hoy", key="topic_study", placeholder="Ej: Energía eólica marina...")

    if st.button("🚀 Generar lección"):
        with st.spinner('Preparando el material...'):
            try:
                style_instruction = "Texto descriptivo" if format_type == "一般短文" else "Diálogo con A: y B:"
                prompt = f"Actúa como profesor de español. Tema: {topic}, Nivel: {level}, Palabras: {word_count}. Formato: {style_instruction}. Formato de salida: [SPANISH] texto [CHINESE] traducción [NOTES] notas."
                response = model.generate_content(prompt)
                full_text = response.text
                
                parts = full_text.split("[CHINESE]")
                spanish_part = parts[0].replace("[SPANISH]", "").strip()
                chinese_part = parts[1].split("[NOTES]")[0].strip()
                notes_part = parts[1].split("[NOTES]")[1].strip()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🇪🇸 Texto en español")
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', spanish_part))
                    combined_audio = b""
                    lines = [line.strip() for line in spanish_part.split('\n') if line.strip()]
                    for line in lines:
                        v = "es-ES-AlvaroNeural" if line.startswith("A:") else "es-ES-ElviraNeural"
                        clip = asyncio.run(get_audio_clip(line.replace("A:","").replace("B:",""), v, speed_val))
                        combined_audio += clip
                    if combined_audio: st.audio(combined_audio, format="audio/mp3")

                with col2:
                    st.subheader("🇹🇼 Traducción")
                    st.markdown(re.sub(r'(A:|B:)', r'\n**\1**', chinese_part))
                st.divider()
                st.success(notes_part)
            except Exception as e:
                st.error(f"Error: {e}")

# ----- Tab 2: 挑戰測驗 (全西語化) -----
with tab2:
    st.title("📝 Centro de Exámenes")
    quiz_topic = st.text_input("Tema del examen", key="topic_quiz", placeholder="Ej: Vocabulario de energía...")
    
    if st.button("🧠 Generar examen en español"):
        with st.spinner('Creando el examen totalmente en español...'):
            try:
                # 這裡強制要求 AI 全程使用西班牙文命題
                quiz_prompt = f"""
                Actúa como un profesor de español profesional. Diseña un examen de nivel {level} sobre el tema "{quiz_topic}".
                TODO EL EXAMEN DEBE ESTAR EN ESPAÑOL.
                
                Contenido del examen:
                1. 10 preguntas de opción múltiple sobre vocabulario (Pregunta y opciones en español).
                2. Un texto corto de 150 palabras relacionado con el tema.
                3. 5 preguntas de comprensión de lectura sobre el texto (Pregunta y opciones en español).
                
                Formato de salida:
                [QUIZ_VOCAB]
                (Preguntas de vocabulario 1-10)
                [QUIZ_READING]
                (Texto y preguntas 11-15)
                [ANSWERS]
                (Solo las letras de las respuestas correctas, ej: 1.A, 2.B...)
                """
                quiz_response = model.generate_content(quiz_prompt)
                quiz_text = quiz_response.text
                
                try:
                    vocab_q = quiz_text.split("[QUIZ_READING]")[0].replace("[QUIZ_VOCAB]", "").strip()
                    reading_q = quiz_text.split("[ANSWERS]")[0].split("[QUIZ_READING]")[1].strip()
                    answers = quiz_text.split("[ANSWERS]")[1].strip()
                    
                    st.subheader("Parte 1: Vocabulario (10 preguntas)")
                    st.markdown(vocab_q)
                    
                    st.divider()
                    st.subheader("Parte 2: Comprensión de lectura (5 preguntas)")
                    st.markdown(reading_q)
                    
                    st.divider()
                    with st.expander("👉 Ver las respuestas correctas (Soluciones)"):
                        st.info(answers)
                        
                except:
                    st.write(quiz_text) 
            except Exception as e:
                st.error(f"Error al generar el examen: {e}")
