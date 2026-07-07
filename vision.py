import os
import base64
import requests

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct:featherless-ai"


def _encode_image_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ask_vision_model(image_path, question):
    b64 = _encode_image_base64(image_path)
    data_url = f"data:image/png;base64,{b64}"

    headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "model": HF_MODEL,
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"I had trouble analyzing the image: {e}"


def describe_screen(question=None):
    import pyautogui

    path = "screenshot.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(path)

    prompt = question or "Describe what's on this screen in one or two sentences."
    result = ask_vision_model(path, prompt)

    try:
        os.remove(path)
    except OSError:
        pass

    return result


def describe_webcam(question=None):
    import cv2

    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    cam.release()

    if not ret:
        return "I couldn't access your webcam."

    path = "webcam.png"
    cv2.imwrite(path, frame)

    prompt = question or "Describe what you see in one or two sentences."
    result = ask_vision_model(path, prompt)

    try:
        os.remove(path)
    except OSError:
        pass

    return result