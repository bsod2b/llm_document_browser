import os
import shutil
from typing import List

from langchain_community.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    TextLoader, CSVLoader, JSONLoader, UnstructuredPDFLoader,PyPDFLoader,
    UnstructuredExcelLoader, UnstructuredHTMLLoader, 
)

FILE_LOADERS = {
    ".txt": TextLoader,
    ".md":  TextLoader,
    ".pdf": PyPDFLoader,
    ".csv": CSVLoader,            # returns BOTH text & DataFrame
    ".json": JSONLoader,
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".html": UnstructuredHTMLLoader,
}

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

def get_vectorstore(persist_dir: str = CHROMA_PATH) -> Chroma:
    """Return a persistent Chroma vector store."""
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",      
        base_url="http://ollama:11434",
        num_thread=4,
    )

    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)

def reset_vectorstore(persist_dir: str = CHROMA_PATH) -> None:
    """Delete the persistent vector store."""
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

def _load_file(path: str) -> List[Document]:
    """Load a file and return its documents."""
    ext = os.path.splitext(path)[1].lower()
    loader_cls = FILE_LOADERS.get(ext)
    if not loader_cls:
        return []
    loader = loader_cls(path)
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = path
    return docs

def ingest_directory(directory: str, persist_dir: str = CHROMA_PATH) -> int:
    """Ingest all supported files in the given directory."""
    docs: List[Document] = []
    for root, _, files in os.walk(directory):
        for name in files:
            print(f"Loading {name}...")
            docs.extend(_load_file(os.path.join(root, name)))
    if not docs:
        return 0
    
    print(f"Loaded {len(docs)} documents")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    print(f"Created {len(splits)} splits")
    
    vectordb = get_vectorstore(persist_dir)
    
    # Process in batches
    batch_size = 32
    for i in range(0, len(splits), batch_size):
        batch = splits[i:i+batch_size]
        progress = f"{min(i+batch_size, len(splits))}/{len(splits)}"
        print(f"Adding batch {progress} ({len(batch)} documents)...")
        vectordb.add_documents(batch)

    return len(splits)

def ingest_files(paths: List[str], persist_dir: str = CHROMA_PATH) -> int:
    """Ingest a list of individual files."""
    docs: List[Document] = []
    for p in paths:
        docs.extend(_load_file(p))
    if not docs:
        return 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    vectordb = get_vectorstore(persist_dir)
    batch_size = 32
    for i in range(0, len(splits), batch_size):
        vectordb.add_documents(splits[i:i+batch_size])
    return len(splits)

def delete_files(paths: List[str], persist_dir: str = CHROMA_PATH) -> None:
    """Remove files and their vectors from the DB."""
    vectordb = get_vectorstore(persist_dir)
    for p in paths:
        if os.path.exists(p):
            os.remove(p)
        vectordb.delete(where={"source": p})

def all_documents(vectordb: Chroma) -> List[Document]:
    """Return all documaents stored in the vector DB."""
    data = vectordb.get(include=["documents", "metadatas"])
    return [Document(page_content=d, metadata=m) for d, m in zip(data["documents"], data["metadatas"])]
