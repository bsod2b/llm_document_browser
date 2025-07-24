import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
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

    llm = OllamaLLM(model="deepseek-r1", temperature=0, reasoning=False)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an assistant that is used for browsing documents. "
                "Use the following context to answer the question."
                "Only use the provided context and sources to answer questions."
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
