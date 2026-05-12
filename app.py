# =========================================
# app.py
# =========================================

from flask import Flask, render_template, request, jsonify
from huggingface_hub import InferenceClient
from PIL import Image
from datetime import datetime
import requests
import urllib.parse
import random
import os
import re

# =========================================
# FLASK
# =========================================

app = Flask(__name__)

# =========================================
# ENV VARIABLES
# =========================================

HF_TOKEN = os.getenv("HF_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

CITY = "Ahmedabad"

# =========================================
# CREATE FOLDERS
# =========================================

os.makedirs("static/op", exist_ok=True)

os.makedirs("static/uploads", exist_ok=True)

os.makedirs("static/combined", exist_ok=True)

# =========================================
# AI MODEL
# =========================================

client = InferenceClient(

    model="meta-llama/Llama-3.1-8B-Instruct",

    token=HF_TOKEN
)

# =========================================
# HOME
# =========================================

@app.route("/")
def home():

    return render_template("index.html")

# =========================================
# IMAGE UPLOAD
# =========================================

@app.route("/upload", methods=["POST"])
def upload_image():

    try:

        if "image" not in request.files:

            return jsonify({

                "success":False,

                "reply":"No image uploaded"
            })

        file = request.files["image"]

        if file.filename == "":

            return jsonify({

                "success":False,

                "reply":"Empty filename"
            })

        filename = (
            f"{random.randint(1,999999)}_"
            f"{file.filename}"
        )

        save_path = os.path.join(

            "static/uploads",

            filename
        )

        file.save(save_path)

        return jsonify({

            "success":True,

            "path":
            f"/static/uploads/{filename}"
        })

    except Exception as e:

        print("UPLOAD ERROR:", e)

        return jsonify({

            "success":False,

            "reply":"Upload failed"
        })

# =========================================
# COMBINE IMAGES
# =========================================

@app.route("/combine", methods=["POST"])
def combine_images():

    try:

        data = request.get_json()

        images = data.get("images", [])

        if len(images) < 2:

            return jsonify({

                "success":False,

                "reply":"Upload at least 2 images"
            })

        pil_images = []

        for img_path in images:

            clean_path = img_path.replace("/", os.sep)

            clean_path = clean_path.lstrip(os.sep)

            image = Image.open(clean_path)

            image = image.convert("RGB")

            pil_images.append(image)

        width = 512

        height = 512

        resized_images = []

        for img in pil_images:

            resized_images.append(

                img.resize((width, height))
            )

        combined = Image.new(

            "RGB",

            (width * len(resized_images), height)
        )

        x = 0

        for img in resized_images:

            combined.paste(img, (x, 0))

            x += width

        filename = (
            f"combined_"
            f"{random.randint(1,999999)}.jpg"
        )

        save_path = os.path.join(

            "static/combined",

            filename
        )

        combined.save(save_path)

        return jsonify({

            "success":True,

            "image":
            f"/static/combined/{filename}"
        })

    except Exception as e:

        print("COMBINE ERROR:", e)

        return jsonify({

            "success":False,

            "reply":"Failed to combine images"
        })

# =========================================
# CHAT API
# =========================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json()

        message = data.get("message", "").strip()

        lower_message = message.lower()

        # =====================================
        # TIME
        # =====================================

        if "time" in lower_message:

            current_time = datetime.now().strftime("%I:%M %p")

            return jsonify({

                "reply":
                f"The current time is {current_time}"
            })

        # =====================================
        # DATE
        # =====================================

        if "date" in lower_message:

            current_date = datetime.now().strftime("%d %B %Y")

            return jsonify({

                "reply":
                f"Today's date is {current_date}"
            })

        # =====================================
        # WEATHER
        # =====================================

        if "weather" in lower_message:

            try:

                if not WEATHER_API_KEY:

                    return jsonify({

                        "reply":
                        "Weather API key missing"
                    })

                url = (

                    f"https://api.openweathermap.org/data/2.5/weather?"
                    f"q={CITY}&appid={WEATHER_API_KEY}&units=metric"
                )

                response = requests.get(url)

                weather_data = response.json()

                temp = weather_data["main"]["temp"]

                desc = weather_data["weather"][0]["description"]

                return jsonify({

                    "reply":

                    f"The temperature in {CITY} "
                    f"is {temp}°C with {desc}"
                })

            except Exception as e:

                print("WEATHER ERROR:", e)

                return jsonify({

                    "reply":
                    "Unable to fetch weather"
                })

        # =====================================
        # IMAGE GENERATION
        # =====================================

        image_keywords = [

            "generate image",
            "create image",
            "make image",
            "draw"
        ]

        if any(word in lower_message for word in image_keywords):

            prompt = lower_message

            for word in image_keywords:

                prompt = prompt.replace(word, "")

            prompt = prompt.strip()

            if prompt == "":

                prompt = "futuristic ai robot"

            enhanced_prompt = (

                "ultra realistic, cinematic lighting, "
                "8k, masterpiece, highly detailed, "
                f"{prompt}"
            )

            encoded_prompt = urllib.parse.quote(

                enhanced_prompt
            )

            seed = random.randint(1,999999)

            image_url = (

                f"https://image.pollinations.ai/p/"
                f"{encoded_prompt}"
                f"?width=1024"
                f"&height=1024"
                f"&seed={seed}"
                f"&model=flux"
            )

            response = requests.get(image_url)

            filename = f"image_{seed}.jpg"

            save_path = os.path.join(

                "static/op",

                filename
            )

            with open(save_path, "wb") as file:

                file.write(response.content)

            return jsonify({

                "reply":
                f"Generated image for: {prompt} 👇",

                "image":
                f"/static/op/{filename}"
            })

        # =====================================
        # AI CHAT
        # =====================================

        response = client.chat_completion(

            messages=[

                {
                    "role":"system",

                    "content":
                    (
                        "You are DIVU, "
                        "a futuristic advanced AI assistant "
                        "created by Kush. "
                        "Reply naturally, intelligently, "
                        "professionally, and warmly. "
                        "Keep answers clean and detailed."
                    )
                },

                {
                    "role":"user",

                    "content":message
                }

            ],

            max_tokens=2000,

            temperature=0.8
        )

        ai_reply = response.choices[0].message.content

        ai_reply = (

            ai_reply
            .replace("*", "")
            .replace('"', "")
            .replace("'", "")
            .replace("```", "")
        )

        ai_reply = re.sub(r'\n+', '\n', ai_reply)

        return jsonify({

            "reply":ai_reply
        })

    except Exception as e:

        print("CHAT ERROR:", e)

        return jsonify({

            "reply":"Server Error"
        })

# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )
