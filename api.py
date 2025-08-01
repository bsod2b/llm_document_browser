import os, json, uuid, asyncio
from typing import List, Literal
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Request, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_experimental.agents import create_pandas_dataframe_agent
from pydantic import BaseModel

from vdb import (
    CHROMA_PATH,
    get_vectorstore,
    ingest_files,
    delete_files,
    all_documents,
)

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatPayload(BaseModel):
    messages: List[Message]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    dest = os.path.join("uploads", file.filename)
    with open(dest, "wb") as f:
        f.write(await file.read())
    count = ingest_files([dest])
    return {"status": "ok", "chunks": count, "file": os.path.basename(dest)}


@app.get("/files")
async def list_files():
    os.makedirs("uploads", exist_ok=True)
    return {"files": os.listdir("uploads")}


@app.delete("/files/{name}")
async def delete_file(name: str):
    path = os.path.join("uploads", name)
    delete_files([path])
    return {"status": "deleted", "file": name}


@app.post("/ask")
async def ask(question: str = Form(...)):
    if not os.path.exists(CHROMA_PATH):
        return {"error": "Vector store not found. Please ingest documents."}

    vectordb = get_vectorstore()
    all_docs = all_documents(vectordb)
    retriever = EnsembleRetriever(
        retrievers=[
            vectordb.as_retriever(search_kwargs={"k": 4}),
            BM25Retriever.from_documents(all_docs),
        ],
        weights=[0.7, 0.3],
    )

    llm = OllamaLLM(
        model="deepseek-r1:8b", 
        temperature=0.2, 
        reasoning=False,
        base_url="http://ollama:11434"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an assistant that is used for browsing documents. "
                "Use the following context to answer the question. "
                "Only use the provided context and sources to answer questions."
                "Keep your answers concise, short and relevant. "
                "Format the answer as markdown, **bold** for important points. "
                "If you are unsure, say so.\n\n{context}",
            ),
            ("human", "{input}"),
        ]
    )
    combine = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, combine)
    result = rag_chain.invoke({"input": question})

    answer = result["answer"]
    sources = {doc.metadata.get("source", "") for doc in result["context"]}

    for doc in result["context"]:
        src = doc.metadata.get("source", "")
        if src.endswith(".csv") and os.path.exists(src):
            df = pd.read_csv(src)
            agent = create_pandas_dataframe_agent(llm, df, verbose=False)
            try:
                csv_answer = agent.run(question)
                answer += "\n\nCSV Analysis:\n" + csv_answer
            except Exception:
                pass

    return {"answer": answer, "sources": list(sources)}

@app.post("/chat")
async def chat(payload: ChatPayload, request: Request):
    """
    Streaming endpoint for Next.js. 
    Produces Server-Sent Events in this shape:
      data: {"id":"...", "delta":"t"}\n\n
      ...
      data: {"id":"...", "final": true}\n\n
      data: [DONE]\n\n
    """

    # Get the latest user question from the payload
    question = ""
    for m in reversed(payload.messages):
        if m.role == "user":
            question = m.content
            break

    if not os.path.exists(CHROMA_PATH):
        # short non-stream error
        return StreamingResponse(iter([
            f'data: {json.dumps({"error":"Vector store not found. Please ingest documents."})}\n\n',
            'data: [DONE]\n\n'
        ]), media_type="text/event-stream")

    vectordb = get_vectorstore()
    all_docs = all_documents(vectordb)

    retriever = EnsembleRetriever(
        retrievers=[
            vectordb.as_retriever(search_kwargs={"k": 4}),
            BM25Retriever.from_documents(all_docs),
        ],
        weights=[0.7, 0.3],
    )

    # You can keep OllamaLLM if you run Ollama in the same Container App.
    # Otherwise, switch to OpenAI/Azure OpenAI here.
    llm = OllamaLLM(
        model="deepseek-r1:8b",
        temperature=0.2,
        reasoning=False,
        base_url=os.getenv("OLLAMA_URL", "http://ollama:11434")
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an assistant that is used for browsing documents. "
                "Use the following context to answer the question. "
                "Only use the provided context and sources to answer questions. "
                "Keep your answers concise, short and relevant. "
                "Format the answer as markdown, **bold** for important points. "
                "If you are unsure, say so.\n\n{context}",
            ),
            ("human", "{input}"),
        ]
    )

    combine = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, combine)

    # We’ll do a simple fake stream (tokenize the final string) to match the
    # client code. If you switch to a truly streaming LLM, stream deltas here.
    async def event_stream():
        try:
            result = rag_chain.invoke({"input": question})
            answer = result["answer"]
            # Optionally append CSV analysis like you do in /ask:
            for doc in result["context"]:
                src = doc.metadata.get("source", "")
                if src.endswith(".csv") and os.path.exists(src):
                    df = pd.read_csv(src)
                    agent = create_pandas_dataframe_agent(llm, df, verbose=False)
                    try:
                        csv_answer = agent.run(question)
                        answer += "\n\nCSV Analysis:\n" + csv_answer
                    except Exception:
                        pass

            msg_id = str(uuid.uuid4())
            for ch in answer:
                if await request.is_disconnected():
                    break
                yield f'data: {json.dumps({"id": msg_id, "delta": ch})}\n\n'
                await asyncio.sleep(0.001)
            yield f'data: {json.dumps({"id": msg_id, "final": True})}\n\n'
            yield "data: [DONE]\n\n"
        except Exception as e:
            err = str(e)
            yield f'data: {json.dumps({"error": err})}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
