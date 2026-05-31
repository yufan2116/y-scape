"""Markdown conversion — txt/html native; pdf/docx best-effort."""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from typing import Any

from src.native_tools.artifact_store import NativeArtifactMeta, NativeArtifactStore, tool_response

TOOL_ID = "markdown_convert"

SUPPORTED = {"txt", "text", "html", "htm", "md", "markdown"}
OPTIONAL = {"pdf", "docx"}


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buf = StringIO()

    def handle_data(self, data: str) -> None:
        self._buf.write(data)

    def get_text(self) -> str:
        return self._buf.getvalue()


def _html_to_md(raw: str) -> str:
    parser = _HTMLToText()
    parser.feed(raw)
    text = html.unescape(parser.get_text())
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n\n".join(f"{ln}" for ln in lines)


def _txt_to_md(raw: str, title: str) -> str:
    if raw.lstrip().startswith("#"):
        return raw
    return f"# {title}\n\n{raw}"


def _convert_content(raw: bytes, source_type: str, filename: str) -> tuple[str | None, str | None]:
    ext = source_type.lower().strip().lstrip(".")
    name = filename or f"input.{ext}"

    if ext in {"txt", "text", "md", "markdown"}:
        text = raw.decode("utf-8", errors="replace")
        md = _txt_to_md(text, Path(name).stem)
        return md, None

    if ext in {"html", "htm"}:
        text = raw.decode("utf-8", errors="replace")
        body = text
        m = re.search(r"<body[^>]*>(.*)</body>", text, re.I | re.S)
        if m:
            body = m.group(1)
        md = f"# {Path(name).stem}\n\n{_html_to_md(body)}"
        return md, None

    if ext == "pdf":
        try:
            import pypdf  # type: ignore[import-untyped]

            from io import BytesIO

            reader = pypdf.PdfReader(BytesIO(raw))
            parts = []
            for i, page in enumerate(reader.pages):
                parts.append(f"## Page {i + 1}\n\n{page.extract_text() or ''}")
            return f"# {Path(name).stem}\n\n" + "\n\n".join(parts), None
        except ImportError:
            return None, "PDF conversion requires pypdf — install with: pip install pypdf"
        except Exception as exc:
            return None, f"PDF conversion failed: {exc}"

    if ext == "docx":
        try:
            import docx  # type: ignore[import-untyped]

            from io import BytesIO

            doc = docx.Document(BytesIO(raw))
            paras = [p.text for p in doc.paragraphs if p.text.strip()]
            return f"# {Path(name).stem}\n\n" + "\n\n".join(paras), None
        except ImportError:
            return None, "DOCX conversion requires python-docx — install with: pip install python-docx"
        except Exception as exc:
            return None, f"DOCX conversion failed: {exc}"

    return None, f"Unsupported source type: {ext}. Supported: {', '.join(sorted(SUPPORTED | OPTIONAL))}"


async def convert_markdown(
    store: NativeArtifactStore,
    *,
    file_bytes: bytes,
    filename: str,
    source_type: str,
    output_filename: str,
) -> dict[str, Any]:
    if not file_bytes:
        return tool_response(ok=False, tool_id=TOOL_ID, error="Empty file upload")

    out_name = output_filename.strip() or f"{Path(filename).stem}.md"
    if not out_name.lower().endswith((".md", ".markdown")):
        out_name += ".md"

    md, err = _convert_content(file_bytes, source_type or Path(filename).suffix.lstrip("."), filename)
    if err:
        return tool_response(ok=False, tool_id=TOOL_ID, error=err)
    if md is None:
        return tool_response(ok=False, tool_id=TOOL_ID, error="Conversion produced no output")

    job_id = store.create_job(TOOL_ID)
    log = {
        "source": filename,
        "sourceType": source_type,
        "output": out_name,
        "bytesIn": len(file_bytes),
        "bytesOut": len(md.encode("utf-8")),
    }

    artifacts: list[NativeArtifactMeta] = []
    artifacts.append(store.write_text(job_id, TOOL_ID, out_name, md, artifact_type="markdown"))
    artifacts.append(
        store.write_text(job_id, TOOL_ID, "conversion_log.json", json.dumps(log, indent=2), artifact_type="json")
    )

    return tool_response(
        ok=True,
        tool_id=TOOL_ID,
        message=f"Converted {filename} → {out_name}",
        artifacts=artifacts,
        data=log,
    )
