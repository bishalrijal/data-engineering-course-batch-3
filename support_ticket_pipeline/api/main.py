"""
main.py — FastAPI backend for the support-ticket chatbot.

Stage 7 of the pipeline: wraps the Stage 5/6 vector search (see
src/vector_store.py, src/query.py) plus a Gemini Flash call into an HTTP
API, so a frontend can ask questions instead of using the query.py CLI.

Run:
    uvicorn api.main:app --reload --port 8000
    (from the support_ticket_pipeline/ directory, with GEMINI_API_KEY set)
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.rag import answer_query
from api.schemas import ChatRequest, ChatResponse

app = FastAPI(
    title="Support Ticket Chatbot API",
    description="Ask a question, get an answer grounded in past support tickets.",
)

# Wide open for local dev with a separate frontend origin; tighten
# allow_origins before deploying this anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = answer_query(req.query, top_k=req.top_k, category=req.category)
    except RuntimeError as e:
        # e.g. missing GEMINI_API_KEY — a config problem, not a server bug
        raise HTTPException(status_code=500, detail=str(e))
    return result
