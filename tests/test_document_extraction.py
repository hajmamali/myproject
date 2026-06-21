import pytest
pytest.importorskip("asyncpg")
from pathlib import Path

from mahoun.pipelines.ingestion.document_handlers import extract_document_text
from api.routers.ingest import _build_upload_response


def test_extract_txt(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("hello txt", encoding="utf-8")

    result = extract_document_text(str(path))
    assert result.success
    assert "hello txt" in result.text
    assert result.metadata.get("extraction_method") == "native"


def test_extract_docx(tmp_path: Path):
    from docx import Document

    path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_paragraph("hello docx")
    doc.save(path)

    result = extract_document_text(str(path))
    assert result.success
    assert "hello docx" in result.text
    assert result.metadata.get("extraction_method") == "python-docx"


def test_extract_pdf(tmp_path: Path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))

    # Add multiple lines to ensure we have >100 characters for successful extraction
    c.drawString(100, 750, "hello pdf")
    c.drawString(100, 730, "This is a test PDF document created for testing purposes.")
    c.drawString(100, 710, "It contains multiple lines of text to ensure proper extraction.")
    c.drawString(100, 690, "The PDF handler should be able to extract this text content.")
    c.drawString(100, 670, "Testing document extraction functionality with pypdf library.")
    c.save()

    result = extract_document_text(str(path))
    assert result.success
    assert "hello pdf" in result.text
    assert result.metadata.get("extraction_method") in ("pypdf", "pdfplumber")


def test_upload_response_bounded(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("hello bounded", encoding="utf-8")

    resp = _build_upload_response(
        str(path),
        filename="sample.txt",
        mime="text/plain",
        include_text=False,
    )
    assert resp["text_length"] == len("hello bounded")
    assert "text" not in resp
    assert resp["text_preview"] == "hello bounded"
