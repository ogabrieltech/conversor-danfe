from __future__ import annotations

import json
import os
import queue
import threading
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import APP_NAME, APP_VERSION, BatchResult, generate_batch, open_folder

def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "ConversorDANFE" / "config.json"


class ConverterApp:
    NAVY = "#071A33"
    NAVY_2 = "#102A4C"
    GREEN = "#28D17C"
    WHITE = "#F6F8FB"
    MUTED = "#AAB8CA"
    BG = "#EAF0F6"

    def __init__(self, root: tk.Tk, initial_sources: list[Path] | None = None):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("900x650")
        self.root.minsize(760, 570)
        self.sources: list[Path] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.processing = False
        self.settings = self._load_settings()

        self.output_var = tk.StringVar(value=self.settings.get("output", ""))
        self.logo_var = tk.StringVar(value=self.settings.get("logo", ""))
        self.overwrite_var = tk.BooleanVar(value=bool(self.settings.get("overwrite", False)))
        self.merge_var = tk.BooleanVar(value=bool(self.settings.get("merge", False)))
        self.open_var = tk.BooleanVar(value=bool(self.settings.get("open", True)))
        self.status_var = tk.StringVar(value="Adicione XMLs, um ZIP ou uma pasta inteira.")
        self.progress_var = tk.DoubleVar(value=0)

        self._build_ui()
        self.root.after(100, self._pump_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if initial_sources:
            self._set_sources(initial_sources)
            self.root.after(450, self.start_conversion)

    def _load_settings(self) -> dict:
        try:
            return json.loads(settings_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_settings(self) -> None:
        path = settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "output": self.output_var.get(), "logo": self.logo_var.get(),
                "overwrite": self.overwrite_var.get(), "merge": self.merge_var.get(),
                "open": self.open_var.get(),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _build_ui(self) -> None:
        self.root.configure(bg=self.BG)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#CED8E5", background=self.GREEN, borderwidth=0)
        style.configure("TCheckbutton", background=self.BG, foreground=self.NAVY, font=("Segoe UI", 10))

        header = tk.Frame(self.root, bg=self.NAVY, height=105)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="NF-e • PDF", bg=self.NAVY, fg=self.GREEN, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=28, pady=(18, 0))
        tk.Label(header, text="Conversor de XML para DANFE", bg=self.NAVY, fg=self.WHITE, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=28)

        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill="both", expand=True, padx=28, pady=20)

        source_card = tk.Frame(body, bg="white", highlightbackground="#D4DDE8", highlightthickness=1)
        source_card.pack(fill="both", expand=True)
        top = tk.Frame(source_card, bg="white")
        top.pack(fill="x", padx=18, pady=(15, 8))
        tk.Label(top, text="1. Arquivos de origem", bg="white", fg=self.NAVY, font=("Segoe UI", 12, "bold")).pack(side="left")
        self._button(top, "Selecionar XML/ZIP", self.choose_files, secondary=True).pack(side="right", padx=(8, 0))
        self._button(top, "Selecionar pasta", self.choose_folder, secondary=True).pack(side="right")

        self.listbox = tk.Listbox(source_card, height=7, bd=0, highlightthickness=0, bg="#F5F8FB", fg=self.NAVY, selectbackground=self.NAVY_2, font=("Segoe UI", 10))
        self.listbox.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        self.listbox.insert(
            "end",
            "Use os botões acima para selecionar arquivos XML, ZIP ou uma pasta.",
        )

        path_area = tk.Frame(body, bg=self.BG)
        path_area.pack(fill="x", pady=(14, 0))
        self._path_row(path_area, "2. Salvar os PDFs em", self.output_var, self.choose_output)
        self._path_row(path_area, "Logo opcional no DANFE", self.logo_var, self.choose_logo, clear=True)

        options = tk.Frame(body, bg=self.BG)
        options.pack(fill="x", pady=(10, 4))
        ttk.Checkbutton(options, text="Criar também um PDF único do lote", variable=self.merge_var).pack(side="left")
        ttk.Checkbutton(options, text="Substituir PDFs existentes", variable=self.overwrite_var).pack(side="left", padx=18)
        ttk.Checkbutton(options, text="Abrir pasta ao concluir", variable=self.open_var).pack(side="left")

        action = tk.Frame(body, bg=self.BG)
        action.pack(fill="x", pady=(12, 0))
        status = tk.Frame(action, bg=self.BG)
        status.pack(side="left", fill="x", expand=True)
        tk.Label(status, textvariable=self.status_var, bg=self.BG, fg=self.NAVY_2, font=("Segoe UI", 10)).pack(anchor="w")
        ttk.Progressbar(status, variable=self.progress_var, maximum=100).pack(fill="x", pady=(6, 0), padx=(0, 20))
        self.convert_button = self._button(action, "GERAR DANFEs", self.start_conversion)
        self.convert_button.pack(side="right", ipadx=18, ipady=7)

        tk.Label(self.root, text="Processamento 100% local • os XMLs não são enviados para a internet", bg=self.NAVY, fg=self.MUTED, font=("Segoe UI", 9)).pack(fill="x", ipady=8)

    def _button(self, parent: tk.Widget, text: str, command: Callable, secondary: bool = False) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, cursor="hand2", bd=0,
            bg="white" if secondary else self.GREEN,
            fg=self.NAVY, activebackground="#DDE8F2" if secondary else "#20B96C",
            activeforeground=self.NAVY, font=("Segoe UI", 10, "bold"), padx=13, pady=8,
            highlightbackground="#CBD6E2", highlightthickness=1 if secondary else 0,
        )

    def _path_row(self, parent: tk.Widget, label: str, variable: tk.StringVar, command: Callable, clear: bool = False) -> None:
        row = tk.Frame(parent, bg=self.BG)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, width=23, anchor="w", bg=self.BG, fg=self.NAVY, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Entry(row, textvariable=variable, relief="flat", bg="white", fg=self.NAVY, font=("Segoe UI", 10), highlightbackground="#CBD6E2", highlightthickness=1).pack(side="left", fill="x", expand=True, ipady=7)
        self._button(row, "Escolher", command, secondary=True).pack(side="left", padx=(8, 0))
        if clear:
            tk.Button(row, text="×", command=lambda: variable.set(""), bd=0, bg=self.BG, fg=self.NAVY, font=("Segoe UI", 14), cursor="hand2").pack(side="left", padx=(5, 0))

    def choose_files(self) -> None:
        files = filedialog.askopenfilenames(title="Selecione XMLs ou ZIPs", filetypes=[("XML e ZIP", "*.xml *.zip"), ("XML", "*.xml"), ("ZIP", "*.zip")])
        if files:
            self._set_sources([Path(p) for p in files])

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecione a pasta que contém os XMLs")
        if folder:
            self._set_sources([Path(folder)])

    def choose_output(self) -> None:
        folder = filedialog.askdirectory(title="Selecione a pasta de destino")
        if folder:
            self.output_var.set(folder)

    def choose_logo(self) -> None:
        logo = filedialog.askopenfilename(title="Selecione a logo", filetypes=[("Imagens", "*.png *.jpg *.jpeg")])
        if logo:
            self.logo_var.set(logo)

    def _set_sources(self, paths: list[Path]) -> None:
        unique: list[Path] = []
        seen = set()
        for path in paths:
            normalized = str(path.resolve()).casefold()
            if normalized not in seen:
                unique.append(path)
                seen.add(normalized)
        self.sources = unique
        self.listbox.delete(0, "end")
        for path in self.sources:
            self.listbox.insert("end", str(path))
        if self.sources:
            first = self.sources[0]
            base = first if first.is_dir() else first.parent
            self.output_var.set(str(base / "DANFEs"))
            self.status_var.set(f"{len(self.sources)} origem(ns) pronta(s) para conversão.")


    def start_conversion(self) -> None:
        if self.processing:
            return
        if not self.sources:
            messagebox.showwarning(APP_NAME, "Selecione ao menos um XML, ZIP ou pasta.")
            return
        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showwarning(APP_NAME, "Selecione a pasta onde os PDFs serão salvos.")
            return
        logo = Path(self.logo_var.get()) if self.logo_var.get().strip() else None
        if logo and not logo.is_file():
            messagebox.showwarning(APP_NAME, "A logo selecionada não foi encontrada.")
            return

        self.processing = True
        self.convert_button.configure(state="disabled", text="CONVERTENDO...")
        self.progress_var.set(0)
        self.status_var.set("Lendo os arquivos...")
        self._save_settings()

        kwargs = {
            "sources": list(self.sources), "output_dir": Path(output_text),
            "overwrite": self.overwrite_var.get(), "merge": self.merge_var.get(), "logo": logo,
        }
        threading.Thread(target=self._worker, kwargs=kwargs, daemon=True).start()

    def _worker(self, **kwargs) -> None:
        try:
            result = generate_batch(**kwargs, progress=lambda i, total, text: self.events.put(("progress", (i, total, text))))
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("fatal", str(exc)))

    def _pump_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "progress":
                    index, total, text = payload
                    self.progress_var.set((index / total * 100) if total else 0)
                    self.status_var.set(f"{index}/{total}: {text}")
                elif event == "done":
                    self._finish(payload)
                elif event == "fatal":
                    self.processing = False
                    self.convert_button.configure(state="normal", text="GERAR DANFEs")
                    self.status_var.set("A conversão não pôde ser concluída.")
                    messagebox.showerror(APP_NAME, f"Erro inesperado:\n\n{payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._pump_events)

    def _finish(self, result: BatchResult) -> None:
        self.processing = False
        self.convert_button.configure(state="normal", text="GERAR DANFEs")
        self.progress_var.set(100)
        self.status_var.set(f"Concluído: {result.generated} gerado(s), {result.skipped} ignorado(s), {result.errors} erro(s).")
        details = (
            f"PDFs gerados: {result.generated}\n"
            f"Ignorados/já existentes: {result.skipped}\n"
            f"Erros: {result.errors}\n\n"
            f"Destino:\n{result.output_dir}\n\n"
            "O relatório CSV informa o resultado de cada arquivo."
        )
        if result.errors:
            messagebox.showwarning("Conversão concluída com avisos", details)
        else:
            messagebox.showinfo("Conversão concluída", details)
        if self.open_var.get():
            try:
                open_folder(result.output_dir)
            except OSError:
                pass

    def _on_close(self) -> None:
        if self.processing and not messagebox.askyesno(APP_NAME, "A conversão ainda está em andamento. Deseja fechar?"):
            return
        self._save_settings()
        self.root.destroy()
