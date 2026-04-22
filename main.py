import base64
import json
import os
import secrets
import zlib

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

API_USERNAME = os.environ["API_USERNAME"]
API_PASSWORD = os.environ["API_PASSWORD"]

app = FastAPI(title="Mermaid SVG API")
security = HTTPBasic()

MERMAID_INK_BASE = "https://mermaid.ink"


def _verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    valid_username = secrets.compare_digest(credentials.username, API_USERNAME)
    valid_password = secrets.compare_digest(credentials.password, API_PASSWORD)
    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def _encode_pako(code: str) -> str:
    payload = json.dumps(
        {"code": code, "mermaid": json.dumps({"theme": "default"})},
        separators=(",", ":"),
    )
    compressed = zlib.compress(payload.encode(), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"pako:{encoded}"


@app.post("/svg")
async def generate_svg(request: Request, _: None = Depends(_verify_credentials)):
    body_bytes = await request.body()
    markdown = body_bytes.decode("utf-8")
    token = _encode_pako(markdown)
    img_url = f"{MERMAID_INK_BASE}/img/{token}"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(img_url)

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


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
