import os
import pandas as pd
import typer
from typing import List

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
    ingest_directory,
    reset_vectorstore,
    all_documents,
)

from dotenv import load_dotenv
load_dotenv()

app = typer.Typer(help="Persistent, Search-Augmented Q&A Engine")


@app.command()
def ingest(path: str = typer.Option(..., help="Directory of documents"), reset: bool = typer.Option(False, help="Reset the database before ingesting")):
    """Ingest documents from a directory."""
    if reset:
        reset_vectorstore()
        typer.echo("Vector store reset.")
    count = ingest_directory(path)
    typer.echo(f"Ingested {count} document chunks.")


@app.command()
def ask(question: str = typer.Argument(..., help="Question to ask")):
    """Ask a question against the document store."""
    vectordb = get_vectorstore()
    if not os.path.exists(CHROMA_PATH):
        typer.echo("Vector store not found. Please ingest documents first.")
        raise typer.Exit(code=1)

    # --- new retrieval layer (vector + BM25) -----------------
    all_docs = all_documents(vectordb)

    retriever = EnsembleRetriever(
        retrievers=[
            vectordb.as_retriever(search_kwargs={"k": 4}), 
            BM25Retriever.from_documents(all_docs)
        ],
        weights=[0.7, 0.3],  # Vector store has more weight
    )  # RRF fusion

    # --- chain that stuffs retrieved docs into the prompt ----
    llm = OllamaLLM(
        model="deepseek-r1", 
        temperature=0.2,
        reasoning=False # thinking mode
    )

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

    typer.echo(result["answer"])
    sources = {doc.metadata.get("source", "") for doc in result["context"]}
    if sources:
        typer.echo("Sources: " + ", ".join(sorted(sources)))

    # CSV tool augmentation
    for doc in result["context"]:
        src = doc.metadata.get("source", "")
        if src.endswith(".csv") and os.path.exists(src):
            df = pd.read_csv(src)
            agent = create_pandas_dataframe_agent(llm, df, verbose=False)
            try:
                csv_answer = agent.run(question)
                typer.echo("\nCSV Analysis:\n" + csv_answer)
            except Exception:
                pass


@app.command()
def status():
    """Show information about the vector database."""
    if not os.path.exists(CHROMA_PATH):
        typer.echo("Vector store empty. Run ingest first.")
        return
    vectordb = get_vectorstore()
    ids = vectordb.get()["ids"]
    typer.echo(f"Stored document chunks: {len(ids)} in {CHROMA_PATH}")


if __name__ == "__main__":
    app()
