import google.generativeai as genai
import os

# Load API key from .env
with open(".env", "r") as f:
    for line in f:
        if line.startswith("GEMINI_API_KEY="):
            api_key = line.split("=")[1].strip()
            break

genai.configure(api_key=api_key)

print("Listing available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
