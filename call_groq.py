import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

def call_groq(prompt, node_name="unknown", max_tokens=512):
    print(f"🐛 [{node_name}] Calling Groq...", flush=True)
    start = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        elapsed = time.time() - start
        print(f"🐛 [{node_name}] Groq responded in {elapsed:.2f}s", flush=True)
        return response.choices[0].message.content
    except Exception as e:
        elapsed = time.time() - start
        print(f"🐛 [{node_name}] Error after {elapsed:.2f}s: {e}", flush=True)
        return f"Error: {e}"