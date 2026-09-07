#!/usr/bin/env python3
"""Recursive Python Code Formatter / Linter GUI.

Standard-library GUI that can use optional external tools when installed:
Black, Ruff, Flake8, Pylint, isort, autopep8.

The program itself only requires Python + Tkinter.
"""

from __future__ import annotations

import ast
import os
import py_compile
import queue
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


APP_TITLE = "Recursive Python Code Formatter & Linter"
DEFAULT_EXCLUDES = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".nox", "venv", ".venv", "env", ".env",
    "build", "dist", "site-packages", "node_modules",
}


@dataclass
class ToolInfo:
    key: str
    label: str
    module: str | None
    executable: str | None = None


TOOLS = [
    ToolInfo("black", "Black formatter", "black"),
    ToolInfo("ruff", "Ruff linter/fixer", "ruff"),
    ToolInfo("flake8", "Flake8 linter", "flake8"),
    ToolInfo("pylint", "Pylint", "pylint"),
    ToolInfo("isort", "isort imports", "isort"),
    ToolInfo("autopep8", "autopep8 formatter", "autopep8"),
]


class CodeFormatterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1120x760")
        self.root.minsize(900, 620)

        self.msg_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.files: list[Path] = []

        self.directory_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.recursive_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)
        self.syntax_var = tk.BooleanVar(value=True)
        self.black_var = tk.BooleanVar(value=True)
        self.ruff_var = tk.BooleanVar(value=True)
        self.flake8_var = tk.BooleanVar(value=True)
        self.pylint_var = tk.BooleanVar(value=False)
        self.isort_var = tk.BooleanVar(value=False)
        self.autopep8_var = tk.BooleanVar(value=False)
        self.ruff_fix_var = tk.BooleanVar(value=False)
        self.exclude_var = tk.StringVar(value=", ".join(sorted(DEFAULT_EXCLUDES)))
        self.extensions_var = tk.StringVar(value=".py")

        self._build_ui()
        self._detect_tools()
        self.root.after(100, self._drain_queue)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        top = ttk.LabelFrame(self.root, text="Source")
        top.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Folder:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.directory_var).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ttk.Button(top, text="Browse...", command=self.choose_directory).grid(row=0, column=2, padx=6, pady=6)
        ttk.Checkbutton(top, text="Recursive", variable=self.recursive_var).grid(row=0, column=3, padx=6, pady=6)

        ttk.Label(top, text="Extensions:").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.extensions_var, width=24).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(top, text="Example: .py, .pyw").grid(row=1, column=2, columnspan=2, padx=6, pady=6, sticky="w")

        ttk.Label(top, text="Exclude folders:").grid(row=2, column=0, padx=6, pady=6, sticky="nw")
        ttk.Entry(top, textvariable=self.exclude_var).grid(row=2, column=1, columnspan=3, padx=6, pady=6, sticky="ew")

        tools = ttk.LabelFrame(self.root, text="Checks and tools")
        tools.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        for c in range(5):
            tools.columnconfigure(c, weight=1)

        ttk.Checkbutton(tools, text="Syntax / compile check", variable=self.syntax_var).grid(row=0, column=0, padx=6, pady=4, sticky="w")
        self.black_cb = ttk.Checkbutton(tools, text="Black", variable=self.black_var)
        self.black_cb.grid(row=0, column=1, padx=6, pady=4, sticky="w")
        self.ruff_cb = ttk.Checkbutton(tools, text="Ruff", variable=self.ruff_var)
        self.ruff_cb.grid(row=0, column=2, padx=6, pady=4, sticky="w")
        self.flake8_cb = ttk.Checkbutton(tools, text="Flake8", variable=self.flake8_var)
        self.flake8_cb.grid(row=0, column=3, padx=6, pady=4, sticky="w")
        self.pylint_cb = ttk.Checkbutton(tools, text="Pylint", variable=self.pylint_var)
        self.pylint_cb.grid(row=0, column=4, padx=6, pady=4, sticky="w")

        self.isort_cb = ttk.Checkbutton(tools, text="isort", variable=self.isort_var)
        self.isort_cb.grid(row=1, column=1, padx=6, pady=4, sticky="w")
        self.autopep8_cb = ttk.Checkbutton(tools, text="autopep8", variable=self.autopep8_var)
        self.autopep8_cb.grid(row=1, column=2, padx=6, pady=4, sticky="w")
        ttk.Checkbutton(tools, text="Ruff --fix during Fix", variable=self.ruff_fix_var).grid(row=1, column=3, padx=6, pady=4, sticky="w")
        ttk.Checkbutton(tools, text="Backup before changes", variable=self.backup_var).grid(row=1, column=4, padx=6, pady=4, sticky="w")

        actions = ttk.Frame(self.root)
        actions.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        actions.columnconfigure(6, weight=1)

        self.scan_btn = ttk.Button(actions, text="1. Scan Files", command=self.scan_files)
        self.scan_btn.grid(row=0, column=0, padx=(0, 6), pady=4)
        self.check_btn = ttk.Button(actions, text="2. Check / Report", command=self.check_all)
        self.check_btn.grid(row=0, column=1, padx=6, pady=4)
        self.fix_btn = ttk.Button(actions, text="3. Format / Fix", command=self.fix_all)
        self.fix_btn.grid(row=0, column=2, padx=6, pady=4)
        self.stop_btn = ttk.Button(actions, text="Stop", command=self.stop_work, state="disabled")
        self.stop_btn.grid(row=0, column=3, padx=6, pady=4)
        ttk.Button(actions, text="Clear Log", command=self.clear_log).grid(row=0, column=4, padx=6, pady=4)
        ttk.Button(actions, text="Tool Status", command=self._detect_tools).grid(row=0, column=5, padx=6, pady=4)
        ttk.Label(actions, textvariable=self.status_var).grid(row=0, column=6, padx=10, pady=4, sticky="e")

        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        file_frame = ttk.LabelFrame(paned, text="Python files")
        log_frame = ttk.LabelFrame(paned, text="Results")
        paned.add(file_frame, weight=2)
        paned.add(log_frame, weight=5)

        file_frame.rowconfigure(0, weight=1)
        file_frame.columnconfigure(0, weight=1)
        self.file_list = tk.Listbox(file_frame, exportselection=False)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        file_scroll = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_list.yview)
        file_scroll.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=file_scroll.set)

        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = ScrolledText(log_frame, wrap="word", font=("TkFixedFont", 10))
        self.log.grid(row=0, column=0, sticky="nsew")

        bottom = ttk.Frame(self.root)
        bottom.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.progress_label = ttk.Label(bottom, text="0 / 0")
        self.progress_label.grid(row=0, column=1)

    # ---------- helpers ----------
    def choose_directory(self) -> None:
        folder = filedialog.askdirectory(title="Select Python source folder")
        if folder:
            self.directory_var.set(folder)
            self.scan_files()

    def _selected_extensions(self) -> set[str]:
        exts = set()
        for item in self.extensions_var.get().replace(";", ",").split(","):
            item = item.strip().lower()
            if not item:
                continue
            if not item.startswith("."):
                item = "." + item
            exts.add(item)
        return exts or {".py"}

    def _excluded_names(self) -> set[str]:
        return {x.strip() for x in self.exclude_var.get().split(",") if x.strip()}

    def _python_module_available(self, module: str) -> bool:
        result = subprocess.run(
            [sys.executable, "-c", f"import importlib.util; raise SystemExit(0 if importlib.util.find_spec('{module}') else 1)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0

    def _detect_tools(self) -> None:
        available = {}
        for tool in TOOLS:
            available[tool.key] = bool(tool.module and self._python_module_available(tool.module))

        controls = {
            "black": (self.black_cb, self.black_var),
            "ruff": (self.ruff_cb, self.ruff_var),
            "flake8": (self.flake8_cb, self.flake8_var),
            "pylint": (self.pylint_cb, self.pylint_var),
            "isort": (self.isort_cb, self.isort_var),
            "autopep8": (self.autopep8_cb, self.autopep8_var),
        }
        for key, (widget, var) in controls.items():
            if available[key]:
                widget.state(["!disabled"])
            else:
                widget.state(["disabled"])
                var.set(False)

        found = [k for k, ok in available.items() if ok]
        missing = [k for k, ok in available.items() if not ok]
        self._log("\nTool detection:\n")
        self._log("  Available: " + (", ".join(found) if found else "none") + "\n")
        self._log("  Missing:   " + (", ".join(missing) if missing else "none") + "\n")
        if missing:
            self._log("  Install optional tools with, for example:\n")
            self._log(f"    {sys.executable} -m pip install black ruff flake8 pylint isort autopep8\n\n")

    def _log(self, text: str) -> None:
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def clear_log(self) -> None:
        self.log.delete("1.0", tk.END)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in (self.scan_btn, self.check_btn, self.fix_btn):
            button.configure(state=state)
        self.stop_btn.configure(state="normal" if busy else "disabled")

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, data = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "status":
                    self.status_var.set(data)
                elif kind == "progress":
                    current, total = map(int, data.split("/"))
                    self.progress["maximum"] = max(total, 1)
                    self.progress["value"] = current
                    self.progress_label.configure(text=f"{current} / {total}")
                elif kind == "done":
                    self._set_busy(False)
                    self.status_var.set(data)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def _start_worker(self, target, *args) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(APP_TITLE, "A task is already running.")
            return
        self.stop_event.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=target, args=args, daemon=True)
        self.worker.start()

    def stop_work(self) -> None:
        self.stop_event.set()
        self.status_var.set("Stopping after current file...")

    # ---------- scanning ----------
    def scan_files(self) -> None:
        folder_text = self.directory_var.get().strip()
        if not folder_text:
            self.choose_directory()
            return
        base = Path(folder_text).expanduser()
        if not base.is_dir():
            messagebox.showerror(APP_TITLE, "Please select a valid folder.")
            return

        exts = self._selected_extensions()
        excludes = self._excluded_names()
        files: list[Path] = []

        if self.recursive_var.get():
            for root, dirs, names in os.walk(base):
                dirs[:] = [d for d in dirs if d not in excludes]
                root_path = Path(root)
                for name in names:
                    p = root_path / name
                    if p.suffix.lower() in exts:
                        files.append(p)
        else:
            files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in exts]

        self.files = sorted(files, key=lambda p: str(p).lower())
        self.file_list.delete(0, tk.END)
        for path in self.files:
            try:
                shown = path.relative_to(base)
            except ValueError:
                shown = path
            self.file_list.insert(tk.END, str(shown))

        self.progress["value"] = 0
        self.progress["maximum"] = max(len(self.files), 1)
        self.progress_label.configure(text=f"0 / {len(self.files)}")
        self.status_var.set(f"Found {len(self.files)} Python file(s)")
        self._log(f"\nScanned: {base}\nFound {len(self.files)} matching file(s).\n")

    # ---------- checking ----------
    def check_all(self) -> None:
        if not self.files:
            self.scan_files()
        if not self.files:
            return
        self._start_worker(self._check_worker)

    def _check_worker(self) -> None:
        total = len(self.files)
        issue_files = 0
        self.msg_queue.put(("log", "\n=== CHECK / REPORT ===\n"))

        for index, path in enumerate(self.files, start=1):
            if self.stop_event.is_set():
                break
            self.msg_queue.put(("status", f"Checking {path.name}"))
            self.msg_queue.put(("progress", f"{index}/{total}"))
            self.msg_queue.put(("log", f"\n--- {path} ---\n"))
            had_issue = False

            if self.syntax_var.get():
                ok, output = self._syntax_check(path)
                self.msg_queue.put(("log", output))
                had_issue |= not ok

            if self.black_var.get():
                rc, output = self._run_module("black", ["--check", "--diff", str(path)])
                self.msg_queue.put(("log", self._format_tool_result("Black", rc, output, ok_codes={0})))
                had_issue |= rc != 0

            if self.ruff_var.get():
                rc, output = self._run_module("ruff", ["check", str(path)])
                self.msg_queue.put(("log", self._format_tool_result("Ruff", rc, output, ok_codes={0})))
                had_issue |= rc != 0

            if self.flake8_var.get():
                rc, output = self._run_module("flake8", [str(path)])
                self.msg_queue.put(("log", self._format_tool_result("Flake8", rc, output, ok_codes={0})))
                had_issue |= rc != 0

            if self.pylint_var.get():
                rc, output = self._run_module("pylint", ["--score=n", str(path)])
                # Pylint uses bit-encoded nonzero exit status for findings.
                self.msg_queue.put(("log", self._format_tool_result("Pylint", rc, output, ok_codes={0})))
                had_issue |= rc != 0

            if self.isort_var.get():
                rc, output = self._run_module("isort", ["--check-only", "--diff", str(path)])
                self.msg_queue.put(("log", self._format_tool_result("isort", rc, output, ok_codes={0})))
                had_issue |= rc != 0

            if self.autopep8_var.get():
                rc, output = self._run_module("autopep8", ["--diff", str(path)])
                # autopep8 --diff normally returns 0 even if it proposes changes.
                if output.strip():
                    self.msg_queue.put(("log", "[autopep8] Suggested changes:\n" + output + "\n"))
                    had_issue = True
                else:
                    self.msg_queue.put(("log", "[autopep8] OK\n"))

            if had_issue:
                issue_files += 1

        if self.stop_event.is_set():
            final = "Check stopped"
            self.msg_queue.put(("log", "\nCheck stopped by user.\n"))
        else:
            final = f"Check complete: {issue_files} file(s) with findings"
            self.msg_queue.put(("log", f"\n=== CHECK COMPLETE: {issue_files} / {total} files had findings ===\n"))
        self.msg_queue.put(("done", final))

    # ---------- fixing ----------
    def fix_all(self) -> None:
        if not self.files:
            self.scan_files()
        if not self.files:
            return

        if not any((self.black_var.get(), self.ruff_fix_var.get() and self.ruff_var.get(), self.isort_var.get(), self.autopep8_var.get())):
            messagebox.showinfo(APP_TITLE, "No formatting/fixing tool is selected.")
            return

        answer = messagebox.askyesno(
            APP_TITLE,
            "This can modify Python files.\n\n"
            + ("Backups are enabled.\n" if self.backup_var.get() else "WARNING: backups are NOT enabled.\n")
            + "Continue?",
        )
        if not answer:
            return
        self._start_worker(self._fix_worker)

    def _fix_worker(self) -> None:
        total = len(self.files)
        changed = 0
        failed = 0
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.msg_queue.put(("log", "\n=== FORMAT / FIX ===\n"))

        for index, path in enumerate(self.files, start=1):
            if self.stop_event.is_set():
                break
            self.msg_queue.put(("status", f"Formatting {path.name}"))
            self.msg_queue.put(("progress", f"{index}/{total}"))
            self.msg_queue.put(("log", f"\n--- {path} ---\n"))

            before = self._safe_read_bytes(path)
            if before is None:
                failed += 1
                self.msg_queue.put(("log", "Could not read file.\n"))
                continue

            backup_path = None
            if self.backup_var.get():
                backup_path = self._make_backup(path, stamp)
                if backup_path:
                    self.msg_queue.put(("log", f"Backup: {backup_path}\n"))
                else:
                    failed += 1
                    self.msg_queue.put(("log", "Backup failed; file was skipped.\n"))
                    continue

            file_failed = False

            if self.isort_var.get():
                rc, output = self._run_module("isort", [str(path)])
                self.msg_queue.put(("log", self._format_tool_result("isort", rc, output, ok_codes={0})))
                file_failed |= rc != 0

            if self.ruff_var.get() and self.ruff_fix_var.get():
                rc, output = self._run_module("ruff", ["check", "--fix", str(path)])
                self.msg_queue.put(("log", self._format_tool_result("Ruff --fix", rc, output, ok_codes={0})))
                file_failed |= rc != 0

            if self.autopep8_var.get():
                rc, output = self._run_module("autopep8", ["--in-place", str(path)])
                self.msg_queue.put(("log", self._format_tool_result("autopep8", rc, output, ok_codes={0})))
                file_failed |= rc != 0

            if self.black_var.get():
                rc, output = self._run_module("black", [str(path)])
                self.msg_queue.put(("log", self._format_tool_result("Black", rc, output, ok_codes={0})))
                file_failed |= rc != 0

            after = self._safe_read_bytes(path)
            if after is not None and after != before:
                changed += 1
                self.msg_queue.put(("log", "Result: changed\n"))
            else:
                self.msg_queue.put(("log", "Result: unchanged\n"))

            ok, syntax_output = self._syntax_check(path)
            self.msg_queue.put(("log", "Post-format " + syntax_output))
            if not ok:
                file_failed = True
                if backup_path:
                    try:
                        shutil.copy2(backup_path, path)
                        self.msg_queue.put(("log", "Syntax check failed; original restored from backup.\n"))
                    except OSError as exc:
                        self.msg_queue.put(("log", f"Could not restore backup: {exc}\n"))

            if file_failed:
                failed += 1

        if self.stop_event.is_set():
            final = "Formatting stopped"
            self.msg_queue.put(("log", "\nFormatting stopped by user.\n"))
        else:
            final = f"Format complete: {changed} changed, {failed} failed"
            self.msg_queue.put(("log", f"\n=== FORMAT COMPLETE: {changed} changed, {failed} failed ===\n"))
        self.msg_queue.put(("done", final))

    # ---------- tool execution ----------
    def _run_module(self, module: str, args: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", module, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=120,
            )
            return proc.returncode, proc.stdout
        except subprocess.TimeoutExpired:
            return 124, f"{module} timed out after 120 seconds.\n"
        except OSError as exc:
            return 127, f"Could not run {module}: {exc}\n"

    def _syntax_check(self, path: Path) -> tuple[bool, str]:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                source = path.read_text(encoding="utf-8-sig")
            except Exception as exc:
                return False, f"[Syntax] Could not decode file: {exc}\n"
        except OSError as exc:
            return False, f"[Syntax] Could not read file: {exc}\n"

        try:
            ast.parse(source, filename=str(path))
            # Also compile without generating __pycache__ in the source tree.
            compile(source, str(path), "exec")
            return True, "[Syntax] OK\n"
        except SyntaxError as exc:
            location = f"line {exc.lineno}, column {exc.offset}" if exc.lineno else "unknown location"
            return False, f"[Syntax] ERROR at {location}: {exc.msg}\n"
        except Exception as exc:
            return False, f"[Syntax] ERROR: {exc}\n"

    def _format_tool_result(self, label: str, rc: int, output: str, ok_codes: set[int]) -> str:
        status = "OK" if rc in ok_codes else f"findings/error (exit {rc})"
        text = f"[{label}] {status}\n"
        if output.strip():
            text += output.rstrip() + "\n"
        return text

    def _safe_read_bytes(self, path: Path) -> bytes | None:
        try:
            return path.read_bytes()
        except OSError:
            return None

    def _make_backup(self, path: Path, stamp: str) -> Path | None:
        try:
            backup_dir = path.parent / ".code_formatter_backups" / stamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / path.name
            counter = 1
            while backup_path.exists():
                backup_path = backup_dir / f"{path.stem}_{counter}{path.suffix}"
                counter += 1
            shutil.copy2(path, backup_path)
            return backup_path
        except OSError:
            return None


if __name__ == "__main__":
    root = tk.Tk()
    app = CodeFormatterApp(root)
    root.mainloop()
