import base64
import json
import zlib

import httpx
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="Mermaid SVG API")

MERMAID_INK_BASE = "https://mermaid.ink"


def _encode_pako(code: str) -> str:
    payload = json.dumps(
        {"code": code, "mermaid": json.dumps({"theme": "default"})},
        separators=(",", ":"),
    )
    compressed = zlib.compress(payload.encode(), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"pako:{encoded}"


@app.post("/svg")
async def generate_svg(request: Request):
    body_bytes = await request.body()
    markdown = body_bytes.decode("utf-8")
    token = _encode_pako(markdown)
    img_url = f"{MERMAID_INK_BASE}/img/{token}"

    with httpx.Client(timeout=15) as client:
        response = client.get(img_url)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"mermaid.ink rendering failed with status {response.status_code}",
        )

    return {
        "svg_url": f"{MERMAID_INK_BASE}/svg/{token}",
        "img_url": img_url,
        "edit_url": f"https://mermaid.live/edit#{token}",
    }
