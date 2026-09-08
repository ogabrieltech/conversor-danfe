from __future__ import annotations

import argparse
from pathlib import Path

from .core import generate_batch


def default_output(sources: list[Path]) -> Path:
    first = sources[0]
    return (first if first.is_dir() else first.parent) / "DANFEs"


def run_cli(args: argparse.Namespace) -> int:
    sources = [Path(p) for p in args.sources]
    result = generate_batch(
        sources,
        Path(args.output) if args.output else default_output(sources),
        overwrite=args.overwrite,
        merge=args.merge,
        logo=Path(args.logo) if args.logo else None,
        progress=lambda i, total, text: print(f"[{i}/{total}] {text}"),
    )
    print(f"Gerados: {result.generated} | Ignorados: {result.skipped} | Erros: {result.errors}")
    print(f"Destino: {result.output_dir}")
    return 1 if result.errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Converte XMLs autorizados de NF-e modelo 55 em DANFEs PDF."
    )
    parser.add_argument("sources", nargs="*", help="XML, ZIP ou pasta")
    parser.add_argument("--output", "-o", help="Pasta de destino")
    parser.add_argument("--merge", action="store_true", help="Cria também um PDF único")
    parser.add_argument("--overwrite", action="store_true", help="Substitui PDFs existentes")
    parser.add_argument("--logo", help="Logo PNG/JPG opcional")
    parser.add_argument("--cli", action="store_true", help="Executa sem interface gráfica")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cli:
        if not args.sources:
            parser.error("informe ao menos uma origem no modo --cli")
        return run_cli(args)

    import tkinter as tk
    from .gui import ConverterApp

    root = tk.Tk()
    ConverterApp(root, [Path(p) for p in args.sources] if args.sources else None)
    root.mainloop()
    return 0
