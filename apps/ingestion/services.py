import csv
import io
import json

from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader


class DocumentExtractionService:
    """Extracts text from supported document types."""

    def extract_text(self, uploaded_document):
        file_type = (uploaded_document.file_type or "").lower()
        if file_type in {"txt", "md"}:
            return uploaded_document.file.read().decode("utf-8", errors="ignore")
        if file_type == "json":
            data = json.loads(uploaded_document.file.read().decode("utf-8", errors="ignore"))
            return json.dumps(data, indent=2)
        if file_type == "html":
            html = uploaded_document.file.read().decode("utf-8", errors="ignore")
            return BeautifulSoup(html, "html.parser").get_text(" ")
        if file_type == "csv":
            content = uploaded_document.file.read().decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(content))
            return "\n".join([", ".join(row) for row in reader])
        if file_type == "pdf":
            reader = PdfReader(uploaded_document.file)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        if file_type == "docx":
            doc = Document(uploaded_document.file)
            return "\n".join([p.text for p in doc.paragraphs])
        return uploaded_document.file.read().decode("utf-8", errors="ignore")


class ChunkingService:
    def chunk(self, text, chunk_size=800, chunk_overlap=120):
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(text):
                break
            start = max(0, end - chunk_overlap)
        return chunks
