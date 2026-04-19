"""GLM-OCR client. Talks to a local Ollama instance running glm-ocr:bf16.

Extraction is a two-phase dance:
1. Render each PDF page to a PNG (pdfium or pillow).
2. Send the rendered image + a JSON-schema-constrained prompt to Ollama and parse the response.

Callers never see the Ollama shape — they get a ``dict[str, Any]`` plus per-field
confidences. Errors surface as ``GLMExtractError`` with a human-readable message;
the router falls through to the fast path or escalates.
"""
from __future__ import annotations

import base64
import io
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

_DEFAULT_URL = "http://localhost:11434"
_DEFAULT_MODEL = "glm-ocr:bf16"
_DEFAULT_NUM_CTX = 16384
_DEFAULT_TIMEOUT = 60.0


class GLMExtractError(Exception):
    """Raised when Ollama is unreachable or returns an unparseable response."""


@dataclass(frozen=True)
class GLMPage:
    index: int
    image_b64: str


def _ollama_url() -> str:
    return os.environ.get("HELIX_OLLAMA_URL", _DEFAULT_URL).rstrip("/")


def _ollama_model() -> str:
    return os.environ.get("HELIX_OLLAMA_MODEL", _DEFAULT_MODEL)


def render_pages(path: Path, *, dpi: int = 200, max_pages: int = 6) -> list[GLMPage]:
    """Render a PDF or image into base64-encoded PNGs for GLM-OCR."""
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError as exc:  # pragma: no cover — dep is in requirements
        raise GLMExtractError(f"pypdfium2 not installed: {exc}") from exc

    pages: list[GLMPage] = []
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        pages.append(GLMPage(index=0, image_b64=_file_to_b64(path)))
        return pages

    pdf = pdfium.PdfDocument(str(path))
    for i, page in enumerate(pdf):
        if i >= max_pages:
            break
        pil = page.render(scale=dpi / 72).to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        pages.append(GLMPage(index=i, image_b64=base64.b64encode(buf.getvalue()).decode("ascii")))
    return pages


def _file_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def extract_with_schema(
    path: Path,
    *,
    prompt: str,
    json_schema: dict[str, Any],
    timeout: float | None = None,
) -> dict[str, Any]:
    """Send rendered pages to Ollama with a JSON schema and return parsed fields."""
    pages = render_pages(path)
    if not pages:
        raise GLMExtractError("no_pages_rendered")
    # GLM-OCR accepts multiple images per call; attach all in one request.
    body = {
        "model": _ollama_model(),
        "prompt": prompt,
        "images": [p.image_b64 for p in pages],
        "format": json_schema,
        "stream": False,
        "options": {"num_ctx": _DEFAULT_NUM_CTX, "temperature": 0.1},
    }
    try:
        with httpx.Client(timeout=timeout or _DEFAULT_TIMEOUT) as client:
            resp = client.post(f"{_ollama_url()}/api/generate", json=body)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise GLMExtractError(f"ollama_unreachable: {exc}") from exc

    raw = resp.json().get("response", "").strip()
    if not raw:
        raise GLMExtractError("empty_response")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GLMExtractError(f"invalid_json_from_model: {exc}: {raw[:200]}") from exc
