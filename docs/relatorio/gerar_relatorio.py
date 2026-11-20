"""Gera o PDF do relatorio a partir de RELATORIO.md.

Uso: python docs/relatorio/gerar_relatorio.py
Requer: pip install markdown  +  Chrome ou Edge instalado (impressao headless).
"""

import subprocess
from pathlib import Path

import markdown

REL = Path(__file__).resolve().parent
PDF = REL / "4992316_Projeto_Back_End.pdf"

CAPA = """
<div class="capa">
  <div class="capa-instituicao">
    <p>PROJETO MULTIDISCIPLINAR &mdash; ELETIVA IV</p>
    <p>TRILHA BACK-END</p>
  </div>
  <div class="capa-titulo">
    <h1>RA&Iacute;ZES DO NORDESTE</h1>
    <h2>API REST multicanal para rede de lanchonetes: pedidos, estoque por unidade,
        fideliza&ccedil;&atilde;o e pagamento desacoplado</h2>
  </div>
  <div class="capa-autor">
    <p>AGATHA SANTANA SOUZA</p>
    <p>RU: 4992316</p>
    <p>Curso: ______________________________</p>
    <p>Polo: ______________________________</p>
  </div>
  <div class="capa-rodape">
    <p>2026</p>
  </div>
</div>
"""

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def numerar_paginas(pdf: Path) -> None:
    """Estampa o número da página no canto superior direito (capa sem número)."""

    try:
        import pymupdf
    except ImportError:
        print("pymupdf ausente: PDF gerado sem numeracao de paginas")
        return

    documento = pymupdf.open(pdf)
    for indice, pagina in enumerate(documento):
        if indice == 0:
            continue
        largura = pagina.rect.width
        pagina.insert_text(
            (largura - 56, 40), str(indice + 1), fontsize=10, fontname="helv"
        )
    temporario = pdf.with_suffix(".tmp.pdf")
    documento.save(temporario)
    documento.close()
    temporario.replace(pdf)


def main() -> None:
    texto = (REL / "RELATORIO.md").read_text(encoding="utf-8").replace("<!--CAPA-->", CAPA)
    corpo = markdown.markdown(
        texto,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    css = (REL / "estilo.css").read_text(encoding="utf-8")

    html = (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        "<title>Raizes do Nordeste - API multicanal</title>\n<style>\n"
        f"{css}\n</style>\n</head>\n<body>\n{corpo}\n</body>\n</html>\n"
    )
    destino_html = REL / "relatorio.html"
    destino_html.write_text(html, encoding="utf-8")
    print(f"HTML: {destino_html}")

    if PDF.exists():
        PDF.unlink()

    for navegador in NAVEGADORES:
        if not Path(navegador).exists():
            continue
        subprocess.run(
            [
                navegador,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=15000",
                f"--print-to-pdf={PDF}",
                destino_html.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if PDF.exists() and PDF.stat().st_size > 50_000:
            numerar_paginas(PDF)
            print(f"PDF: {PDF} ({PDF.stat().st_size // 1024} KB)")
            return

    raise SystemExit("Nenhum navegador disponivel para gerar o PDF")


if __name__ == "__main__":
    main()
