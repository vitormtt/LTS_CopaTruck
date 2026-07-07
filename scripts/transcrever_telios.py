import os
import glob
import base64
import json
import time
import urllib.request
import urllib.error

API_KEY = os.getenv("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
DIR = "/home/vitor/Projects/SARU/partnerships/lts-copatruck/docs/Telios imagens"
OUT_FILE = "/home/vitor/Projects/SARU/partnerships/lts-copatruck/docs/Telios_prints_transcricao.md"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def transcribe_image(image_path):
    base64_img = encode_image(image_path)
    data = {
        "contents": [{
            "parts": [
                {"text": "Transcreva todo o texto contido nesta imagem. Se houver tabelas, listas ou elementos de interface, formate-os organizadamente em markdown."},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64_img
                    }
                }
            ]
        }]
    }
    
    req = urllib.request.Request(URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read()
            res_json = json.loads(res_body)
            return res_json['candidates'][0]['content']['parts'][0]['text']
    except urllib.error.HTTPError as e:
        return f"ERRO HTTP AO TRANSCREVER: {e.code} - {e.read().decode()}"
    except Exception as e:
        return f"ERRO GERAL: {str(e)}"

images = sorted(glob.glob(os.path.join(DIR, "*.png")))
total = len(images)

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("# Transcrição de Prints (Telios)\n\n")

for i, img_path in enumerate(images):
    img_name = os.path.basename(img_path)
    print(f"[{i+1}/{total}] Transcrevendo {img_name}...")
    
    text = transcribe_image(img_path)
    
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"## {img_name}\n\n")
        f.write(text.strip())
        f.write("\n\n---\n\n")
    
    time.sleep(2.0)

print(f"\nFinalizado! Salvo em {OUT_FILE}")
