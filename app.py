from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import google.generativeai as genai
import os

app = FastAPI()

# 確保抓取 Vercel 的環境變數
API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)

# 終極 HTML 介面：嵌入 CSS 排版、過濾 Markdown 符號與多國口音系統
html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>西語 2.5 Flash 旗艦家教</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-top: 0; }
        .control-panel { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 25px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 8px; color: #34495e; }
        input[type="text"], select { width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        .slider-container { display: flex; align-items: center; gap: 15px; }
        input[type="range"] { flex: 1; }
        .btn { background-color: #e74c3c; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.3s; width: 100%; }
        .btn:hover { background-color: #c0392b; }
        .btn:disabled { background-color: #bdc3c7; cursor: not-allowed; }
        
        /* 教材排版區塊樣式 */
        .card { border-radius: 8px; padding: 20px; margin-top: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); line-height: 1.8; font-size: 17px; }
        .spanish-box { background-color: #eef9f6; border-left: 6px solid #1abc9c; color: #111; font-weight: 500; margin-bottom: 20px; }
        .chinese-box { background-color: #fffde7; border-left: 6px solid #f1c40f; color: #555; font-style: italic; margin-bottom: 20px; }
        .vocab-box { background-color: #fdf2f2; border-left: 6px solid #e74c3c; color: #c0392b; margin-bottom: 20px; }
        .grammar-box { background-color: #f4f6f7; border-left: 6px solid #7f8c8d; color: #2c3e50; }
        
        /* 重點單字粗體與亮底 */
        strong { font-weight: bold; color: #d35400; background-color: #ffeaa7; padding: 2px 4px; border-radius: 4px; }
        
        /* 語音控制區 */
        .audio-controls { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        .audio-btn { flex: 1; min-width: 150px; background-color: #34495e; color: white; border: none; padding: 10px; border-radius: 20px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .audio-btn:hover { background-color: #2c3e50; }
        
        #loading { display: none; text-align: center; font-weight: bold; color: #e74c3c; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🇪🇸 西語 2.5 Flash 旗艦家教</h1>
        
        <div class="control-panel">
            <form id="generator-form">
                <div class="form-group">
                    <label for="topic">請輸入想練習的實用主題：</label>
                    <input type="text" id="topic" name="topic" placeholder="例如：在仙台居酒屋點餐、與朋友聊聊假期、4歲小孩基礎西文..." required>
                </div>
                
                <div class="form-group">
                    <label>口音與語系設定：</label>
                    <select id="accent-select">
                        <option value="es-ES">🇪🇸 西班牙本土口音 (Castellano)</option>
                        <option value="es-MX">🇲🇽 墨西哥口音 (Mexicano)</option>
                        <option value="es-US">🇺🇸 美國地區西語</option>
                        <option value="es-AR">🇦🇷 阿根廷口音 (Rioplatense)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="speed">調整語速 (0.5x - 1.5x)：</label>
                    <div class="slider-container">
                        <input type="range" id="speed" name="speed" min="0.5" max="1.5" step="0.1" value="0.9">
                        <span id="speed-val">0.9x</span>
                    </div>
                </div>
                
                <button type="submit" class="btn" id="submit-btn">🪄 生成客製化教材</button>
            </form>
        </div>

        <div id="loading">⏳ 老師正在努力撰寫精華教材（固定 250 字），請稍候...</div>
        <div id="result-area"></div>
    </div>

    <script>
        // 語速滑桿數值即時更新
        document.getElementById('speed').addEventListener('input', function(e) {
            document.getElementById('speed-val').innerText = e.target.value + 'x';
        });

        // 表單提交與 AJAX 請求
        document.getElementById('generator-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('submit-btn');
            const loading = document.getElementById('loading');
            const resultArea = document.getElementById('result-area');
            const topic = document.getElementById('topic').value;

            submitBtn.disabled = true;
            loading.style.display = 'block';
            resultArea.innerHTML = '';

            try {
                const formData = new FormData();
                formData.append('topic', topic);

                const response = await fetch('/api/generate', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.status === 'success') {
                    // 渲染漂亮的區塊化卡片
                    resultArea.innerHTML = `
                        <div class="audio-controls">
                            <button class="audio-btn" onclick="playLesson('charA')">🗣️ 角色 A 朗讀 (低音調)</button>
                            <button class="audio-btn" onclick="playLesson('charB')">🗣️ 角色 B 朗讀 (高音調)</button>
                            <button class="audio-btn" style="background-color:#7f8c8d;" onclick="window.speechSynthesis.cancel()">⏹️ 停止播放</button>
                        </div>
                        <div class="card spanish-box"><h3>✨ 西文原文 (Texto)</h3><p id="spanish-content">${data.spanish}</p></div>
                        <div class="card chinese-box"><h3>💡 中文翻譯 (Traducción)</h3><p>${data.chinese}</p></div>
                        <div class="card vocab-box"><h3>📌 重要單字 (Vocabulario)</h3><p>${data.vocab}</p></div>
                        <div class="card grammar-box"><h3>📝 文法解析 (Gramática)</h3><p>${data.grammar}</p></div>
                    `;
                    // 將隱藏的原文供語音包讀取（已移除 Markdown 符號）
                    window.rawSpanishText = data.raw_spanish;
                } else {
                    resultArea.innerHTML = `<p style="color:red;">❌ 錯誤：${data.message}</p>`;
                }
            } catch (err) {
                resultArea.innerHTML = `<p style="color:red;">❌ 連線失敗，請檢查網路或 API Key。</p>`;
            } finally {
                submitBtn.disabled = false;
                loading.style.display = 'none';
            }
        });

        // 核心語音合成優化功能（過濾星號、切換角色與口音）
        function playLesson(character) {
            const synth = window.speechSynthesis;
            if (!window.rawSpanishText) return;
            
            // 安全解鎖：防止重複播放疊音
            synth.cancel();

            // 1. 純淨化文字：過濾掉任何可能殘留的 ** 或星號
            let cleanText = window.rawSpanishText.replace(/\\*/g, '');

            const msg = new SpeechSynthesisUtterance(cleanText);
            
            // 2. 口音設定：動態抓取選單中的國家代碼 (es-ES, es-MX 等)
            const selectedLang = document.getElementById('accent-select').value;
            msg.lang = selectedLang;

            // 智慧尋找對應口音的內建語音包（部分瀏覽器支援）
            const voices = synth.getVoices();
            const matchedVoice = voices.find(v => v.lang.includes(selectedLang));
            if (matchedVoice) {
                msg.voice = matchedVoice;
            }

            // 3. 語速控制
            const speed = document.getElementById('speed').value;
            msg.rate = parseFloat(speed);

            // 4. 雙角色聲音模擬 (透過調整音調 Pitch 區隔)
            if (character === 'charA') {
                msg.pitch = 0.8; // 渾厚低沉音（適合模擬男聲或慢速澄清音）
            } else if (character === 'charB') {
                msg.pitch = 1.3; // 輕快高昂音（適合模擬女聲或日常對話感）
            }

            synth.speak(msg);
        }

        // 讓部分瀏覽器提前加載語音包
        window.speechSynthesis.getVoices();
    </script>
</body>
</html>
"""

@app.get("/")
def read_root():
    return HTMLResponse(content=html_content)

@app.get("/api/healthcheck")
def healthcheck():
    return {"status": "ok", "model": "gemini-2.5-flash"}

@app.post("/api/generate")
def generate_lesson(topic: str = Form(...)):
    # 建立強大且格式嚴格的 250 字 Prompt 指令
    prompt = f"""
    你是最溫柔、專業的西班牙語老師。請針對主題「{topic}」，為 A2-B1 等級的學生設計一份實用教材。
    請嚴格遵守以下格式規範，不要自創額外的標籤，字數必須剛好固定在 250 字左右：

    [SPANISH]
    這裡寫西班牙文小短文或雙人對話（如果是對話，請明確寫出角色名字如 Juan:, Maria:）。
    請將需要學生注意的「重要單字或片語」用 Markdown 的粗體標籤 ** 包裹起來，例如：**artesanía**。

    [CHINESE]
    這裡寫整篇西班牙文的「繁體中文」翻譯。

    [VOCAB]
    列出短文中被加粗的重要單字，格式為：**單字** (中文解釋)。每個單字換行。

    [GRAMMAR]
    列出 1-2 個實用的文法或句型重點解析。
    """
    
    try:
        # 使用你已經成功打通的 2.5 Flash 引擎
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.text

        # 進行精準的區塊結構切分
        spanish_section = ""
        chinese_section = ""
        vocab_section = ""
        grammar_section = ""

        if "[SPANISH]" in text and "[CHINESE]" in text and "[VOCAB]" in text and "[GRAMMAR]" in text:
            parts = text.split("[SPANISH]")[1].split("[CHINESE]")
            spanish_section = parts[0].strip()
            
            parts = parts[1].split("[VOCAB]")
            chinese_section = parts[0].strip()
            
            parts = parts[1].split("[GRAMMAR]")
            vocab_section = parts[0].strip()
            grammar_section = parts[1].strip()
        else:
            # 防呆降級處理
            spanish_section = text
            chinese_section = "教材格式生成不夠完美，請再點選一次生成。"

        # 為 HTML 顯示保留 Markdown 粗體語法 (將 ** 轉成 HTML 的 <strong>)
        html_spanish = spanish_section.replace("\n", "<br>").replace("**", "<strong>", 1).replace("**", "</strong>")
        while "**" in html_spanish:
            html_spanish = html_spanish.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

        html_vocab = vocab_section.replace("\n", "<br>").replace("**", "<strong>", 1).replace("**", "</strong>")
        while "**" in html_vocab:
            html_vocab = html_vocab.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

        # 創造一份完全乾淨、沒有 ** 星號的純文字，專門給語音朗讀使用
        raw_spanish_text = spanish_section.replace("**", "")

        return {
            "status": "success",
            "spanish": html_spanish,
            "chinese": chinese_section.replace("\n", "<br>"),
            "vocab": html_vocab,
            "grammar": grammar_section.replace("\n", "<br>"),
            "raw_spanish": raw_spanish_text
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
