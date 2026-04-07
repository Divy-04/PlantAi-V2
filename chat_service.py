import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama-3.3-70b-versatile"   # bigger model = better language compliance

LANG_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
}

SYSTEM_PROMPT = """You are PlantAI Assistant — a friendly plant disease expert.

Detected plant disease information:
  Disease : {disease}
  Cause   : {cause}
  Cure    : {cure}

CRITICAL LANGUAGE RULE:
You MUST write every single response ONLY in {lang_name}.
It does not matter what language the user types in.
You MUST always respond in {lang_name} and nothing else.
Never use English unless {lang_name} IS English.
Never mix languages. Every word must be in {lang_name}.

Other rules:
- Simple, warm, practical language a farmer can understand.
- Keep answers concise.
- Always remember the detected disease above.
"""


def get_reply(disease: str, cause: str, cure: str,
              language: str, user_message: str, history: list) -> str:

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in .env file")

    lang_name   = LANG_NAMES.get(language, "English")
    system_text = SYSTEM_PROMPT.format(
        disease=disease, cause=cause, cure=cure, lang_name=lang_name
    )

    messages = [{"role": "system", "content": system_text}]

    # Add history — skip internal language instruction prefix from old messages
    for msg in history:
        role    = "assistant" if msg["role"] == "model" else msg["role"]
        content = msg["content"]
        if content.startswith("[IMPORTANT:"):
            content = content.split("]\n\n", 1)[-1]
        messages.append({"role": role, "content": content})

    # Two-shot language enforcement pattern before the actual question
    messages.append({
        "role": "user",
        "content": f"Remember: reply ONLY in {lang_name}."
    })
    messages.append({
        "role": "assistant",
        "content": f"Understood, I will reply only in {lang_name}."
    })

    # Actual user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json"
        },
        json={
            "model":       MODEL,
            "messages":    messages,
            "temperature": 0.4,
            "max_tokens":  600,
        },
        timeout=30
    )

    if not response.ok:
        if response.status_code == 429:
            raise RuntimeError("AI request limit reached. Please try again in a moment.")
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

    return response.json()["choices"][0]["message"]["content"]