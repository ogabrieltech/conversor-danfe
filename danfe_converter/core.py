from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable
import xml.etree.ElementTree as ET

APP_NAME = "Conversor DANFE"
APP_VERSION = "1.1.0"
AUTHORIZED_CODES = {"100", "150"}
MAX_XML_BYTES = 50 * 1024 * 1024
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def first_descendant(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((node for node in parent.iter() if local_name(node.tag) == name), None)


def child_text(parent: ET.Element | None, name: str, default: str = "") -> str:
    node = first_descendant(parent, name)
    return (node.text or "").strip() if node is not None else default


def decode_xml(data: bytes) -> str:
    declaration = data[:250]
    match = re.search(br'encoding=["\']([^"\']+)', declaration, re.IGNORECASE)
    encodings = []
    if match:
        encodings.append(match.group(1).decode("ascii", errors="ignore"))
    encodings.extend(["utf-8-sig", "iso-8859-1"])
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    return data.decode("utf-8", errors="replace")


def safe_filename(value: str, max_length: int = 105) -> str:
    value = INVALID_FILENAME.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if not value:
        value = "SEM NOME"
    if value.upper() in WINDOWS_RESERVED:
        value = f"_{value}"
    return value[:max_length].rstrip(" .")


@dataclass(frozen=True)
class XmlDocument:
    source: str
    data: bytes


@dataclass(frozen=True)
class InvoiceInfo:
    number: str
    series: str
    recipient: str
    access_key: str
    issue_date: str
    status_code: str
    status_reason: str
    model: str

    @property
    def authorized(self) -> bool:
        return self.status_code in AUTHORIZED_CODES


@dataclass
class BatchResult:
    generated: int
    skipped: int
    errors: int
    output_dir: Path
    report_path: Path
    merged_path: Path | None = None


def parse_invoice(data: bytes) -> InvoiceInfo:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"XML inválido: {exc}") from exc

    root_name = local_name(root.tag)
    if root_name not in {"nfeProc", "NFe"}:
        if root_name == "LOTE":
            raise ValueError("XML de pedidos; não é uma NF-e fiscal")
        raise ValueError(f"Documento '{root_name}' não é uma NF-e")

    nfe = root if root_name == "NFe" else first_descendant(root, "NFe")
    inf_nfe = first_descendant(nfe, "infNFe")
    if inf_nfe is None:
        raise ValueError("Estrutura infNFe não encontrada")

    ide = first_descendant(inf_nfe, "ide")
    dest = first_descendant(inf_nfe, "dest")
    prot = first_descendant(root, "infProt")
    model = child_text(ide, "mod")
    if model != "55":
        label = model or "não informado"
        raise ValueError(f"Modelo {label} não suportado; esperado NF-e modelo 55")

    inf_id = inf_nfe.attrib.get("Id", "")
    key_from_id = inf_id[3:] if inf_id.startswith("NFe") else ""
    access_key = child_text(prot, "chNFe") or key_from_id
    status_code = child_text(prot, "cStat")
    status_reason = child_text(prot, "xMotivo")

    return InvoiceInfo(
        number=child_text(ide, "nNF", "SEM NUMERO"),
        series=child_text(ide, "serie"),
        recipient=child_text(dest, "xNome", "SEM DESTINATARIO"),
        access_key=access_key,
        issue_date=child_text(ide, "dhEmi") or child_text(ide, "dEmi"),
        status_code=status_code,
        status_reason=status_reason,
        model=model,
    )


def read_zip(path: Path) -> tuple[list[XmlDocument], list[tuple[str, str]]]:
    documents: list[XmlDocument] = []
    issues: list[tuple[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith(".xml")]
            if not members:
                issues.append((str(path), "ZIP sem arquivos XML"))
            for member in members:
                source = f"{path.name} :: {member.filename}"
                if member.file_size > MAX_XML_BYTES:
                    issues.append((source, "XML maior que 50 MB"))
                    continue
                try:
                    documents.append(XmlDocument(source, archive.read(member)))
                except Exception as exc:
                    issues.append((source, f"Não foi possível ler: {exc}"))
    except (OSError, zipfile.BadZipFile) as exc:
        issues.append((str(path), f"ZIP inválido: {exc}"))
    return documents, issues


def collect_documents(sources: Iterable[Path]) -> tuple[list[XmlDocument], list[tuple[str, str]]]:
    documents: list[XmlDocument] = []
    issues: list[tuple[str, str]] = []
    candidates: list[Path] = []

    for source in sources:
        if source.is_dir():
            candidates.extend(
                sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in {".xml", ".zip"})
            )
        elif source.is_file() and source.suffix.lower() in {".xml", ".zip"}:
            candidates.append(source)
        else:
            issues.append((str(source), "Arquivo ou pasta não encontrado/suportado"))

    seen_paths: set[str] = set()
    for path in candidates:
        identity = str(path.resolve()).casefold()
        if identity in seen_paths:
            continue
        seen_paths.add(identity)
        if path.suffix.lower() == ".zip":
            docs, zip_issues = read_zip(path)
            documents.extend(docs)
            issues.extend(zip_issues)
            continue
        try:
            if path.stat().st_size > MAX_XML_BYTES:
                issues.append((str(path), "XML maior que 50 MB"))
            else:
                documents.append(XmlDocument(str(path), path.read_bytes()))
        except OSError as exc:
            issues.append((str(path), f"Não foi possível ler: {exc}"))
    return documents, issues


def unique_pdf_path(output_dir: Path, info: InvoiceInfo, occupied: set[Path]) -> Path:
    base = safe_filename(f"NF {info.number} - {info.recipient}")
    candidate = output_dir / f"{base}.pdf"
    if candidate not in occupied:
        occupied.add(candidate)
        return candidate
    suffix = info.access_key[-8:] if info.access_key else info.series or "duplicada"
    candidate = output_dir / f"{base} - {safe_filename(suffix)}.pdf"
    index = 2
    while candidate in occupied:
        candidate = output_dir / f"{base} - {safe_filename(suffix)} ({index}).pdf"
        index += 1
    occupied.add(candidate)
    return candidate


def load_danfe_library():
    try:
        from brazilfiscalreport.danfe import Danfe, DanfeConfig
    except ImportError as exc:
        raise RuntimeError(
            "Dependência BrazilFiscalReport não encontrada. "
            "Instale as dependências com: pip install -r requirements.txt"
        ) from exc
    return Danfe, DanfeConfig


def generate_batch(
    sources: list[Path],
    output_dir: Path,
    *,
    overwrite: bool = False,
    merge: bool = False,
    logo: Path | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> BatchResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    documents, scan_issues = collect_documents(sources)
    rows: list[dict[str, str]] = []
    for source, message in scan_issues:
        rows.append({
            "origem": source,
            "resultado": "ERRO",
            "nf": "",
            "destinatario": "",
            "pdf": "",
            "mensagem": message,
        })

    parsed: list[tuple[XmlDocument, InvoiceInfo]] = []
    for document in documents:
        try:
            parsed.append((document, parse_invoice(document.data)))
        except Exception as exc:
            rows.append({"origem": document.source, "resultado": "IGNORADO", "nf": "", "destinatario": "", "pdf": "", "mensagem": str(exc)})

    parsed.sort(key=lambda item: (item[1].issue_date, item[1].number, item[0].source))
    occupied: set[Path] = set()
    seen_keys: set[str] = set()
    pdfs_for_merge: list[Path] = []
    generated = 0
    skipped = sum(1 for row in rows if row["resultado"] == "IGNORADO")
    errors = sum(1 for row in rows if row["resultado"] == "ERRO")
    total = len(parsed)

    Danfe, DanfeConfig = load_danfe_library()
    config = DanfeConfig(logo=str(logo)) if logo and logo.is_file() else None
    for index, (document, info) in enumerate(parsed, 1):
        if progress:
            progress(index, total, f"NF {info.number} — {info.recipient}")

        identity = info.access_key or f"{info.number}|{info.series}|{info.recipient}|{info.issue_date}"
        if identity in seen_keys:
            skipped += 1
            rows.append({"origem": document.source, "resultado": "IGNORADO", "nf": info.number, "destinatario": info.recipient, "pdf": "", "mensagem": "NF-e duplicada no lote"})
            continue
        seen_keys.add(identity)

        if not info.authorized:
            reason = "NF-e sem protocolo de autorização"
            if info.status_code:
                reason = f"NF-e não autorizada: {info.status_code} {info.status_reason}".strip()
            skipped += 1
            rows.append({"origem": document.source, "resultado": "IGNORADO", "nf": info.number, "destinatario": info.recipient, "pdf": "", "mensagem": reason})
            continue

        pdf_path = unique_pdf_path(output_dir, info, occupied)
        if pdf_path.exists() and not overwrite:
            skipped += 1
            pdfs_for_merge.append(pdf_path)
            rows.append({"origem": document.source, "resultado": "JÁ EXISTIA", "nf": info.number, "destinatario": info.recipient, "pdf": str(pdf_path), "mensagem": "PDF preservado"})
            continue

        temporary = pdf_path.with_suffix(".pdf.tmp")
        try:
            danfe = Danfe(xml=decode_xml(document.data), config=config)
            danfe.output(str(temporary))
            os.replace(temporary, pdf_path)
            generated += 1
            pdfs_for_merge.append(pdf_path)
            rows.append({"origem": document.source, "resultado": "GERADO", "nf": info.number, "destinatario": info.recipient, "pdf": str(pdf_path), "mensagem": "OK"})
        except Exception as exc:
            errors += 1
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            rows.append({"origem": document.source, "resultado": "ERRO", "nf": info.number, "destinatario": info.recipient, "pdf": str(pdf_path), "mensagem": str(exc)})

    merged_path: Path | None = None
    if merge and pdfs_for_merge:
        try:
            from pypdf import PdfWriter

            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            merged_path = output_dir / f"DANFEs - Lote {stamp}.pdf"
            writer = PdfWriter()
            for pdf_path in pdfs_for_merge:
                writer.append(str(pdf_path))
            with merged_path.open("wb") as handle:
                writer.write(handle)
            writer.close()
        except Exception as exc:
            errors += 1
            rows.append({"origem": "LOTE", "resultado": "ERRO", "nf": "", "destinatario": "", "pdf": "", "mensagem": f"Falha ao criar PDF único: {exc}"})
            merged_path = None

    report_path = output_dir / f"Relatório da conversão - {datetime.now():%Y-%m-%d_%H%M%S}.csv"
    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["origem", "resultado", "nf", "destinatario", "pdf", "mensagem"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    return BatchResult(generated, skipped, errors, output_dir, report_path, merged_path)


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
