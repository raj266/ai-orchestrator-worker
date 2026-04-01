from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time
import json
from call_groq import call_groq

app = FastAPI(title="Orchestrator-Worker - Hospitality")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Mock Workers (replace with real APIs later) ----------
def worker_flights(origin: str, destination: str, travel_date: str, budget: str) -> str:
    # Simulated flight search
    return f"✈️ Flights from {origin} to {destination} around {travel_date}: IndiGo ₹4,500, SpiceJet ₹5,200, Air India ₹6,800."

def worker_hotels(destination: str, check_in: str, check_out: str, budget: str, preferences: str) -> str:
    # Simulated hotel search
    return f"🏨 Hotels in {destination} ({check_in} to {check_out}): Beachfront Resort ₹8,000/night, City Central Hotel ₹5,500/night."

def worker_activities(destination: str, duration_days: int, interests: str) -> str:
    # Simulated activity suggestions
    return f"🎉 Suggested activities in {destination} ({duration_days} days): Sunset cruise, spice plantation tour, water sports."

# ---------- Orchestrator: decompose query into tasks ----------
def orchestrator(query: str):
    prompt = f"""You are a travel planning orchestrator. Read the user's request and list the specific tasks needed.

User request: {query}

Output a JSON array of objects with fields: "worker" (one of "flights", "hotels", "activities"), and "params" (an object with keys relevant to that worker).

Example:
[
  {{"worker": "flights", "params": {{"origin": "Bangalore", "destination": "Goa", "travel_date": "December 15", "budget": "10000"}}}},
  {{"worker": "hotels", "params": {{"destination": "Goa", "check_in": "December 15", "check_out": "December 20", "budget": "25000", "preferences": "beachfront"}}}},
  {{"worker": "activities", "params": {{"destination": "Goa", "duration_days": 5, "interests": "romantic, water sports"}}}}
]
Only output the JSON array, nothing else.
"""
    response = call_groq(prompt, node_name="ORCHESTRATOR")
    try:
        tasks = json.loads(response)
        return tasks
    except json.JSONDecodeError:
        # Fallback: parse with regex
        import re
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            try:
                tasks = json.loads(match.group())
                return tasks
            except:
                return []
        return []

# ---------- Worker dispatcher ----------
def execute_task(task):
    worker = task["worker"]
    params = task["params"]
    if worker == "flights":
        return worker_flights(**params)
    elif worker == "hotels":
        return worker_hotels(**params)
    elif worker == "activities":
        return worker_activities(**params)
    else:
        return f"Unknown worker: {worker}"

# ---------- Synthesizer ----------
def synthesizer(query: str, tasks_results):
    prompt = f"""You are a travel itinerary synthesizer. Use the results from different specialists to create a day‑by‑day travel plan.

User request: {query}

Specialist results:
{json.dumps(tasks_results, indent=2)}

Create a friendly, detailed itinerary (include day‑by‑day breakdown if possible). Keep it under 500 words.
"""
    return call_groq(prompt, node_name="SYNTHESIZER")

# ---------- API endpoint ----------
class OrchestrateRequest(BaseModel):
    query: str

class OrchestrateResponse(BaseModel):
    final_answer: str
    steps: list
    elapsed_time: float

@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    start = time.time()
    steps = []

    # 1. Orchestrator
    tasks = orchestrator(request.query)
    steps.append({"step": "orchestrator", "output": json.dumps(tasks, indent=2)})

    # 2. Execute each task
    results = []
    for task in tasks:
        result = execute_task(task)
        results.append({"task": task, "result": result})
        steps.append({"step": f"worker_{task['worker']}", "output": result})

    # 3. Synthesizer
    final = synthesizer(request.query, results)
    steps.append({"step": "synthesizer", "output": final})

    elapsed = time.time() - start
    return OrchestrateResponse(final_answer=final, steps=steps, elapsed_time=elapsed)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)