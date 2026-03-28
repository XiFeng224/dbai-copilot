from __future__ import annotations

import os
import shutil
import uuid

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import EMBEDDING_MODEL


def make_session_id() -> str:
    return uuid.uuid4().hex


def _get_embedder():
    # Use local sentence-transformers embeddings.
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def build_or_replace_index(docs: list[Document], persist_dir: str) -> Chroma:
    """
    建立/重建向量庫。
    docs 先粗切後再做更細的 chunking。
    """
    # Ensure persist_dir is clean to avoid mixing old docs.
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)

    os.makedirs(persist_dir, exist_ok=True)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=80,
        separators=["\n\n", "\n", " ", ""],
    )
    split_docs = splitter.split_documents(docs)

    # Chroma stores text + metadata.
    embedding = _get_embedder()
    vs = Chroma.from_documents(
        documents=split_docs,
        embedding=embedding,
        persist_directory=persist_dir,
    )
    vs.persist()
    return vs


def retrieve_context(vs: Chroma, query: str, top_k: int = 5) -> tuple[str, list[Document]]:
    retriever = vs.as_retriever(search_kwargs={"k": top_k})
    docs = retriever.get_relevant_documents(query)

    context_blocks: list[str] = []
    for i, d in enumerate(docs, start=1):
        src = d.metadata.get("source", "unknown")
        page = d.metadata.get("page")
        para = d.metadata.get("paragraph")
        chunk = d.metadata.get("chunk")

        where = ""
        if page:
            where = f"页{page}"
        elif para:
            where = f"段落{para}"
        elif chunk:
            where = f"段{chunk}"

        context_blocks.append(
            f"[片段{i}] 来源={src} {where}\n{d.page_content}"
        )

    return "\n\n".join(context_blocks), docs

