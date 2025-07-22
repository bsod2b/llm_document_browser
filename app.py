import os
import pandas as pd
import typer
from typing import List

from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain_community.retrievers import BM25Retriever
from langchain_community.llms import Ollama
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

    vector_docs = vectordb.similarity_search(question, k=4)
    all_docs = all_documents(vectordb)
    bm25 = BM25Retriever.from_documents(all_docs)
    keyword_docs = bm25.get_relevant_documents(question)

    # combine results deduplicating by page content
    unique = {}
    for doc in vector_docs + keyword_docs:
        key = doc.page_content[:100]
        if key not in unique:
            unique[key] = doc
    docs: List = list(unique.values())[:6]

    llm = Ollama(model="deepseek-r1", temperature=0)
    chain = load_qa_with_sources_chain(llm, chain_type="stuff")
    result = chain({"question": question, "input_documents": docs}, return_only_outputs=True)

    typer.echo(result["output_text"])
    if result.get("sources"):
        typer.echo(f"Sources: {result['sources']}")

    # CSV tool augmentation
    for doc in docs:
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
