"""Renderiza os diagramas Mermaid de docs/diagramas para PNG e SVG via Kroki.

Uso: python docs/diagramas/renderizar.py
Requer conexao com a internet (https://kroki.io) e httpx instalado.
"""

import base64
import re
import zlib
from pathlib import Path

import httpx

DIAG = Path(__file__).resolve().parent
IMG = DIAG / "img"


def codificar(definicao: str) -> str:
    return base64.urlsafe_b64encode(zlib.compress(definicao.encode("utf-8"), 9)).decode().rstrip("=")


def main() -> None:
    IMG.mkdir(exist_ok=True)
    client = httpx.Client(timeout=60)

    for arquivo in sorted(DIAG.glob("*.md")):
        blocos = re.findall(r"```mermaid\s*\n(.*?)```", arquivo.read_text(encoding="utf-8"), re.S)
        for indice, bloco in enumerate(blocos, start=1):
            nome = f"{arquivo.stem}-{indice}"
            for formato in ("png", "svg"):
                destino = IMG / f"{nome}.{formato}"
                resposta = client.get(
                    f"https://kroki.io/mermaid/{formato}/{codificar(bloco)}"
                )
                if resposta.status_code == 200:
                    destino.write_bytes(resposta.content)
                    print(f"ok {destino.name}")
                else:
                    print(f"falha {destino.name}: {resposta.status_code}")


if __name__ == "__main__":
    main()
