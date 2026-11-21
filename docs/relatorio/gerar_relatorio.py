"""Gera o PDF do relatorio (ABNT) a partir de RELATORIO.md.

Etapas: monta capa e folha de rosto, gera sumario com numeros de pagina
(duas passadas), anexa o contrato de endpoints extraido do OpenAPI e
exporta o PDF com paginacao a partir da introducao.

Uso: python docs/relatorio/gerar_relatorio.py
Requer: pip install markdown pymupdf  +  Chrome ou Edge instalado.
"""

import re
import subprocess
import sys
from html import escape
from pathlib import Path

import markdown

REL = Path(__file__).resolve().parent
REPO = REL.parents[1]
PDF = REL / "4992316_Projeto_Back_End.pdf"
sys.path.insert(0, str(REPO))

INSTITUICAO = "CENTRO UNIVERSITÁRIO INTERNACIONAL UNINTER"
CIDADE = "JACAREÍ – SÃO PAULO"
AUTOR = "AGATHA SANTANA SOUZA"
RU = "4992316"
ANO = "2026"
TITULO = "RAÍZES DO NORDESTE"
SUBTITULO = (
    "API REST multicanal para rede de lanchonetes: pedidos, estoque por unidade, "
    "fidelização e pagamento desacoplado"
)
PROFESSOR = "Prof. Me. Luciane Yanase Kanashiro"
DISCIPLINA = "Projeto Multidisciplinar – Eletiva IV (Trilha Back-End)"

CAPA = f"""
<div class="capa">
  <div class="capa-topo"><p>{INSTITUICAO}</p></div>
  <div class="capa-meio">
    <p class="capa-autor">{AUTOR}</p>
    <p class="capa-ru">RU: {RU}</p>
    <h1 class="capa-titulo">{TITULO}</h1>
    <h2 class="capa-subtitulo">{SUBTITULO}</h2>
  </div>
  <div class="capa-base"><p>{CIDADE}</p><p>{ANO}</p></div>
</div>
<div class="page-break"></div>
<div class="folha-rosto">
  <div class="fr-topo"><p>{AUTOR}</p><p class="fr-ru">RU: {RU}</p></div>
  <div class="fr-titulo">
    <h1 class="capa-titulo">{TITULO}</h1>
    <h2 class="capa-subtitulo">{SUBTITULO}</h2>
  </div>
  <div class="fr-natureza">
    <p>Trabalho apresentado como requisito parcial da disciplina {DISCIPLINA}, do
       {INSTITUICAO}, para fins de avaliação da Atividade Prática.</p>
    <p class="fr-professor">Professor(a) responsável: {PROFESSOR}</p>
  </div>
  <div class="capa-base"><p>{CIDADE}</p><p>{ANO}</p></div>
</div>
"""

IGNORAR_NO_SUMARIO = {"SUMÁRIO", "RESUMO"}


def extrair_titulos(texto: str) -> list[tuple[int, str]]:
    titulos: list[tuple[int, str]] = []
    dentro_de_bloco = False
    for linha in texto.splitlines():
        if linha.strip().startswith("```"):
            dentro_de_bloco = not dentro_de_bloco
            continue
        if dentro_de_bloco:
            continue
        encontrado = re.match(r"^(#{1,2})\s+(.*)$", linha)
        if not encontrado:
            continue
        titulo = encontrado.group(2).strip()
        if titulo.upper() in IGNORAR_NO_SUMARIO:
            continue
        titulos.append((len(encontrado.group(1)), titulo))
    return titulos


def montar_sumario(titulos, paginas: dict[str, int] | None = None) -> str:
    linhas = []
    for nivel, titulo in titulos:
        pagina = str(paginas.get(titulo, "")) if paginas else ""
        classe = "toc-n1" if nivel == 1 else "toc-n2"
        linhas.append(
            f'<div class="toc-item {classe}">'
            f'<span class="toc-texto">{escape(titulo)}</span>'
            f'<span class="toc-pontos"></span>'
            f'<span class="toc-pagina">{pagina}</span></div>'
        )
    return '<div class="sumario">' + "\n".join(linhas) + "</div>"


def apendice_d() -> str:
    """Gera a tabela de contrato por endpoint a partir do OpenAPI real."""

    from app.main import app

    spec = app.openapi()
    linhas = [
        "# APÊNDICE D — CONTRATO POR ENDPOINT (GERADO DO OPENAPI)",
        "",
        "Tabela extraída automaticamente da especificação OpenAPI servida pela própria aplicação, "
        "o que garante correspondência exata entre documentação e implementação. "
        "Parâmetros marcados com asterisco são obrigatórios.",
        "",
        "| Método | Rota | Auth | Parâmetros | Corpo | Respostas |",
        "|---|---|---|---|---|---|",
    ]

    for rota, metodos in sorted(spec["paths"].items()):
        for metodo, operacao in metodos.items():
            if metodo not in {"get", "post", "put", "patch", "delete"}:
                continue
            auth = "JWT" if operacao.get("security") else "público"

            parametros = []
            for parametro in operacao.get("parameters", []):
                marca = "*" if parametro.get("required") else ""
                parametros.append(f"`{parametro['name']}` ({parametro['in']}){marca}")

            corpo = "—"
            conteudo = operacao.get("requestBody", {}).get("content", {})
            if conteudo:
                esquema = next(iter(conteudo.values())).get("schema", {})
                referencia = esquema.get("$ref", "")
                corpo = referencia.split("/")[-1] if referencia else "objeto"

            respostas = ", ".join(sorted(operacao.get("responses", {})))
            linhas.append(
                f"| {metodo.upper()} | `{rota}` | {auth} | "
                f"{escape(', '.join(parametros)) or '—'} | {corpo} | {respostas} |"
            )
    return "\n".join(linhas)


def envolver_referencias(html: str) -> str:
    abertura = html.find("<h1>REFERÊNCIAS</h1>")
    if abertura == -1:
        return html
    fim_tag = html.find("</h1>", abertura) + len("</h1>")
    proximo_h1 = html.find("<h1", fim_tag)
    if proximo_h1 == -1:
        proximo_h1 = len(html)
    return (
        html[:fim_tag]
        + '<div class="referencias">'
        + html[fim_tag:proximo_h1]
        + "</div>"
        + html[proximo_h1:]
    )


def montar_html(texto: str, sumario: str) -> str:
    texto = texto.replace("<!--CAPA-->", CAPA)
    texto = texto.replace("<!--SUMARIO-->", sumario)
    texto = texto.replace("<!--APENDICE-D-->", apendice_d())

    corpo = markdown.markdown(
        texto,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    corpo = envolver_referencias(corpo)

    css = (REL / "estilo.css").read_text(encoding="utf-8")
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        "<title>Raizes do Nordeste - API multicanal</title>\n<style>\n"
        f"{css}\n</style>\n</head>\n<body>\n{corpo}\n</body>\n</html>\n"
    )


NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def imprimir_pdf(html_path: Path) -> None:
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
                html_path.as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if PDF.exists() and PDF.stat().st_size > 50_000:
            return
    raise SystemExit("Nenhum navegador disponivel para gerar o PDF")


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip().lower()


def localizar_paginas(titulos) -> tuple[dict[str, int], int, int]:
    """Retorna (pagina de cada titulo, total de paginas, indice da introducao).

    O casamento é por linha inteira: evita que "referências" no meio de um
    parágrafo seja confundido com o título da seção.
    """

    import pymupdf

    documento = pymupdf.open(PDF)
    linhas_por_pagina = [
        [normalizar(linha) for linha in pagina.get_text("text").splitlines() if linha.strip()]
        for pagina in documento
    ]
    total = documento.page_count
    documento.close()

    paginas: dict[str, int] = {}
    alvo_intro = normalizar(titulos[0][1])

    # A introdução começa em página nova e é o primeiro elemento dela. A busca
    # de todos os títulos parte daí, o que exclui naturalmente o sumário.
    inicio = next(
        (
            indice
            for indice, linhas in enumerate(linhas_por_pagina)
            if linhas and linhas[0] == alvo_intro
        ),
        len(linhas_por_pagina) - 1,
    )

    for _, titulo in titulos:
        alvo = normalizar(titulo)
        prefixo = alvo[:40]
        for indice in range(inicio, total):
            linhas = linhas_por_pagina[indice]
            if linhas and (linhas[0] == alvo or linhas[0].startswith(prefixo)):
                paginas[titulo] = indice
                break
            if any(linha == alvo for linha in linhas):
                paginas[titulo] = indice
                break

    return paginas, total, inicio


def numerar_paginas(indice_introducao: int) -> None:
    """ABNT: conta da folha de rosto, exibe a partir da introducao."""

    import pymupdf

    documento = pymupdf.open(PDF)
    for indice, pagina in enumerate(documento):
        if indice < indice_introducao:
            continue
        pagina.insert_text(
            (pagina.rect.width - 56, 40), str(indice), fontsize=10, fontname="helv"
        )
    temporario = PDF.with_suffix(".tmp.pdf")
    documento.save(temporario)
    documento.close()
    temporario.replace(PDF)


def main() -> None:
    texto = (REL / "RELATORIO.md").read_text(encoding="utf-8")
    titulos = extrair_titulos(texto)
    titulos.append((1, "APÊNDICE D — CONTRATO POR ENDPOINT (GERADO DO OPENAPI)"))
    destino_html = REL / "relatorio.html"

    paginas: dict[str, int] | None = None
    indice_introducao = 99
    total_anterior = -1

    for passada in range(1, 4):
        html = montar_html(texto, montar_sumario(titulos, paginas))
        destino_html.write_text(html, encoding="utf-8")
        imprimir_pdf(destino_html)

        paginas, total, indice_introducao = localizar_paginas(titulos)
        faltando = [t for _, t in titulos if t not in paginas]
        if faltando:
            print(f"passada {passada}: {len(faltando)} titulo(s) sem pagina", faltando[:3])
        if total == total_anterior and not faltando:
            break
        total_anterior = total

    numerar_paginas(indice_introducao)
    print(f"PDF: {PDF} ({PDF.stat().st_size // 1024} KB, {total} paginas)")


if __name__ == "__main__":
    main()
