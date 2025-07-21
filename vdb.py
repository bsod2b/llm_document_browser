import os
import shutil
from typing import List

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.document_loaders import TextLoader, CSVLoader, PyPDFLoader

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

def get_vectorstore(persist_dir: str = CHROMA_PATH) -> Chroma:
    """Return a persistent Chroma vector store."""
    embeddings = OpenAIEmbeddings()
    return Chroma(persist_directory=persist_dir, embedding_function=embeddings)

def reset_vectorstore(persist_dir: str = CHROMA_PATH) -> None:
    """Delete the persistent vector store."""
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

def _load_file(path: str) -> List[Document]:
    if path.endswith(".txt"):
        loader = TextLoader(path)
    elif path.endswith(".csv"):
        loader = CSVLoader(path)
    elif path.endswith(".pdf"):
        loader = PyPDFLoader(path)
    else:
        return []
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = path
    return docs

def ingest_directory(directory: str, persist_dir: str = CHROMA_PATH) -> int:
    """Ingest all supported files in the given directory."""
    docs: List[Document] = []
    for root, _, files in os.walk(directory):
        for name in files:
            docs.extend(_load_file(os.path.join(root, name)))
    if not docs:
        return 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)
    vectordb = get_vectorstore(persist_dir)
    vectordb.add_documents(splits)
    vectordb.persist()
    return len(splits)

def all_documents(vectordb: Chroma) -> List[Document]:
    """Return all documents stored in the vector DB."""
    data = vectordb.get(include=["documents", "metadatas"])
    return [Document(page_content=d, metadata=m) for d, m in zip(data["documents"], data["metadatas"])]
