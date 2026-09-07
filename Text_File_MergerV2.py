#!/usr/bin/env python3

"""
Text File Merger V2
Standard-library-only Tkinter utility.

Features:
- Add individual files
- Add all files from a folder, optionally recursively
- Reorder files before merging
- Sort files by path
- Remove selected files / clear list
- Choose the exact output filename
- Optional filename headers and separators
- UTF-8 output
- Safer input decoding with fallback encodings
- Progress/status display
"""

import os
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class FileMergerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Text File Merger V2")
        self.geometry("850x560")
        self.minsize(700, 450)

        self.selected_files = []

        self.recursive_var = tk.BooleanVar(value=True)
        self.add_headers_var = tk.BooleanVar(value=True)
        self.add_separator_var = tk.BooleanVar(value=True)
        self.blank_lines_var = tk.IntVar(value=1)

        self._build_gui()
        self._update_status()

    def _build_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---------- Top controls ----------
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        for col in range(8):
            top.columnconfigure(col, weight=0)
        top.columnconfigure(7, weight=1)

        ttk.Button(top, text="Add Files", command=self.add_files).grid(
            row=0, column=0, padx=3, pady=3
        )
        ttk.Button(top, text="Add Folder", command=self.add_folder).grid(
            row=0, column=1, padx=3, pady=3
        )
        ttk.Checkbutton(
            top, text="Recursive", variable=self.recursive_var
        ).grid(row=0, column=2, padx=(8, 3), pady=3)

        ttk.Button(top, text="Remove Selected", command=self.remove_selected).grid(
            row=0, column=3, padx=3, pady=3
        )
        ttk.Button(top, text="Clear", command=self.clear_files).grid(
            row=0, column=4, padx=3, pady=3
        )
        ttk.Button(top, text="Sort", command=self.sort_files).grid(
            row=0, column=5, padx=3, pady=3
        )

        # ---------- File list ----------
        list_frame = ttk.LabelFrame(self, text="Files to merge", padding=6)
        list_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            activestyle="dotbox",
            exportselection=False,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview
        )
        yscroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=yscroll.set)

        xscroll = ttk.Scrollbar(
            list_frame, orient="horizontal", command=self.listbox.xview
        )
        xscroll.grid(row=1, column=0, sticky="ew")
        self.listbox.configure(xscrollcommand=xscroll.set)

        move_frame = ttk.Frame(list_frame)
        move_frame.grid(row=0, column=2, padx=(8, 0), sticky="ns")
        ttk.Button(move_frame, text="Move Up", command=self.move_up).grid(
            row=0, column=0, sticky="ew", pady=(0, 5)
        )
        ttk.Button(move_frame, text="Move Down", command=self.move_down).grid(
            row=1, column=0, sticky="ew"
        )

        # ---------- Options ----------
        options = ttk.LabelFrame(self, text="Merge options", padding=8)
        options.grid(row=2, column=0, padx=8, pady=(0, 8), sticky="ew")

        ttk.Checkbutton(
            options,
            text="Add source filename before each file",
            variable=self.add_headers_var,
        ).grid(row=0, column=0, padx=3, pady=3, sticky="w")

        ttk.Checkbutton(
            options,
            text="Add separator between files",
            variable=self.add_separator_var,
        ).grid(row=0, column=1, padx=12, pady=3, sticky="w")

        ttk.Label(options, text="Blank lines between files:").grid(
            row=0, column=2, padx=(12, 3), pady=3
        )
        ttk.Spinbox(
            options,
            from_=0,
            to=10,
            width=5,
            textvariable=self.blank_lines_var,
        ).grid(row=0, column=3, padx=3, pady=3)

        # ---------- Bottom ----------
        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )

        self.progress = ttk.Progressbar(bottom, mode="determinate", length=220)
        self.progress.grid(row=0, column=1, padx=8)

        ttk.Button(
            bottom,
            text="Merge and Save...",
            command=self.merge_files,
        ).grid(row=0, column=2, padx=(6, 0))

    # ---------- File list management ----------

    def add_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select text files to merge",
            filetypes=[
                ("Text and data files", "*.txt *.log *.csv *.rtf *.md *.ini *.cfg"),
                ("All files", "*.*"),
            ],
        )

        if file_paths:
            self._add_unique_paths(file_paths)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing files")
        if not folder:
            return

        folder_path = Path(folder)

        try:
            if self.recursive_var.get():
                paths = [p for p in folder_path.rglob("*") if p.is_file()]
            else:
                paths = [p for p in folder_path.iterdir() if p.is_file()]
        except OSError as exc:
            messagebox.showerror("Folder Error", str(exc))
            return

        paths.sort(key=lambda p: str(p).lower())
        self._add_unique_paths(str(p) for p in paths)

    def _add_unique_paths(self, paths):
        existing = set(self.selected_files)

        for path in paths:
            normalized = os.path.abspath(os.fspath(path))
            if normalized not in existing:
                self.selected_files.append(normalized)
                existing.add(normalized)

        self._refresh_listbox()

    def remove_selected(self):
        selected = list(self.listbox.curselection())
        if not selected:
            return

        for index in reversed(selected):
            del self.selected_files[index]

        self._refresh_listbox()

    def clear_files(self):
        if not self.selected_files:
            return

        if messagebox.askyesno("Clear List", "Remove all files from the list?"):
            self.selected_files.clear()
            self._refresh_listbox()

    def sort_files(self):
        self.selected_files.sort(key=str.lower)
        self._refresh_listbox()

    def move_up(self):
        selected = list(self.listbox.curselection())
        if not selected or selected[0] == 0:
            return

        for index in selected:
            self.selected_files[index - 1], self.selected_files[index] = (
                self.selected_files[index],
                self.selected_files[index - 1],
            )

        self._refresh_listbox()
        for index in (i - 1 for i in selected):
            self.listbox.selection_set(index)

    def move_down(self):
        selected = list(self.listbox.curselection())
        if not selected or selected[-1] == len(self.selected_files) - 1:
            return

        for index in reversed(selected):
            self.selected_files[index + 1], self.selected_files[index] = (
                self.selected_files[index],
                self.selected_files[index + 1],
            )

        self._refresh_listbox()
        for index in (i + 1 for i in selected):
            self.listbox.selection_set(index)

    def _refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for path in self.selected_files:
            self.listbox.insert(tk.END, path)

        self._update_status()

    def _update_status(self, extra=""):
        count = len(self.selected_files)
        text = f"{count} file{'s' if count != 1 else ''} selected"
        if extra:
            text += f"  |  {extra}"
        self.status_var.set(text)

    # ---------- Reading / merging ----------

    @staticmethod
    def read_text_file(path):
        """
        Try common encodings used by Linux and Windows text files.
        The final UTF-8 attempt replaces undecodable bytes rather than
        aborting the entire merge.
        """
        encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as input_file:
                    return input_file.read()
            except UnicodeDecodeError:
                continue

        with open(path, "r", encoding="utf-8", errors="replace") as input_file:
            return input_file.read()

    def merge_files(self):
        if not self.selected_files:
            messagebox.showwarning("No Files", "Select at least one file first.")
            return

        default_name = time.strftime("merged_%Y-%m-%d_%H-%M-%S.txt")

        output_path = filedialog.asksaveasfilename(
            title="Save merged file",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("Text file", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not output_path:
            return

        output_path = os.path.abspath(output_path)

        input_paths = {os.path.abspath(path) for path in self.selected_files}
        if output_path in input_paths:
            messagebox.showerror(
                "Invalid Output",
                "The output file cannot be one of the files being merged.",
            )
            return

        total = len(self.selected_files)
        self.progress.configure(maximum=total, value=0)
        self.update_idletasks()

        try:
            with open(output_path, "w", encoding="utf-8", newline="\n") as output_file:
                for number, file_path in enumerate(self.selected_files, start=1):
                    self._update_status(
                        f"Merging {number} of {total}: {os.path.basename(file_path)}"
                    )
                    self.update_idletasks()

                    text = self.read_text_file(file_path)

                    if self.add_headers_var.get():
                        output_file.write(
                            f"===== {os.path.basename(file_path)} =====\n"
                        )

                    output_file.write(text)

                    # Ensure the next section starts on a new line.
                    if text and not text.endswith(("\n", "\r")):
                        output_file.write("\n")

                    if self.add_separator_var.get() and number < total:
                        output_file.write("-" * 72)
                        output_file.write("\n")

                    if number < total:
                        output_file.write("\n" * max(0, self.blank_lines_var.get()))

                    self.progress["value"] = number
                    self.update_idletasks()

        except (OSError, UnicodeError) as exc:
            self._update_status("Merge failed")
            messagebox.showerror("Merge Error", f"Could not merge the files:\n\n{exc}")
            return
        except Exception as exc:
            self._update_status("Unexpected error")
            messagebox.showerror("Unexpected Error", str(exc))
            return

        self._update_status(f"Saved: {output_path}")
        messagebox.showinfo(
            "Merge Complete",
            f"Merged {total} files successfully.\n\nSaved as:\n{output_path}",
        )


if __name__ == "__main__":
    app = FileMergerApp()
    app.mainloop()
