
import os
import re
import unicodedata
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class RecursiveRenamer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recursive In-Place File Renamer")
        self.geometry("1120x760")
        self.minsize(900, 620)

        self.files = []
        self.last_rename = []

        self.folder_var = tk.StringVar()
        self.extension_var = tk.StringVar(value="*")
        self.include_hidden_var = tk.BooleanVar(value=False)

        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.regex_var = tk.BooleanVar(value=False)
        self.case_sensitive_var = tk.BooleanVar(value=False)

        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.case_var = tk.StringVar(value="No change")
        self.space_var = tk.StringVar(value="No change")
        self.remove_chars_var = tk.StringVar()
        self.remove_accents_var = tk.BooleanVar(value=False)

        self.number_mode_var = tk.StringVar(value="None")
        self.number_start_var = tk.IntVar(value=1)
        self.number_step_var = tk.IntVar(value=1)
        self.number_padding_var = tk.IntVar(value=3)
        self.number_separator_var = tk.StringVar(value="_")

        self.extension_case_var = tk.StringVar(value="No change")
        self.status_var = tk.StringVar(
            value="Choose a root folder. Subfolders will be searched recursively."
        )

        self.build_gui()
        self.bind_preview_updates()

    def build_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(
            top,
            text="Recursive In-Place File Renamer",
            font=("TkDefaultFont", 14, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        ttk.Label(top, text="Root folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.folder_var).grid(
            row=1, column=1, sticky="ew", padx=6
        )
        ttk.Button(
            top, text="Choose Folder...", command=self.choose_folder
        ).grid(row=1, column=2, padx=4)
        ttk.Button(
            top, text="Scan Again", command=self.scan_folder
        ).grid(row=1, column=3)

        ttk.Label(top, text="Extensions:").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(top, textvariable=self.extension_var, width=28).grid(
            row=2, column=1, sticky="w", padx=6, pady=(6, 0)
        )
        ttk.Label(
            top, text="Examples: *   .jpg   .jpg,.png,.txt"
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Checkbutton(
            top,
            text="Include hidden files/folders",
            variable=self.include_hidden_var,
            command=self.scan_folder
        ).grid(row=3, column=1, sticky="w", pady=(5, 0))

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew", padx=10)

        options = ttk.Frame(body, padding=(0, 0, 8, 0))
        preview = ttk.Frame(body)
        body.add(options, weight=0)
        body.add(preview, weight=1)

        self.build_options(options)
        self.build_preview(preview)

        bottom = ttk.Frame(self, padding=10)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        ttk.Label(bottom, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            bottom, text="Reset Options", command=self.reset_options
        ).grid(row=0, column=1, padx=4)
        ttk.Button(
            bottom, text="Undo Last Batch", command=self.undo_last
        ).grid(row=0, column=2, padx=4)
        ttk.Button(
            bottom,
            text="RENAME FILES IN PLACE",
            command=self.rename_files
        ).grid(row=0, column=3, padx=(12, 0))

    def build_options(self, parent):
        parent.columnconfigure(0, weight=1)

        warning = ttk.LabelFrame(parent, text="Mode", padding=8)
        warning.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            warning,
            text="Files stay in their original folders."
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            warning,
            text="Only filenames change; existing files are never overwritten."
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        box = ttk.LabelFrame(parent, text="Find and Replace", padding=8)
        box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Find:").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.find_var).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Label(box, text="Replace:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(box, textvariable=self.replace_var).grid(
            row=1, column=1, sticky="ew", padx=5, pady=4
        )
        ttk.Checkbutton(
            box, text="Regular expression", variable=self.regex_var
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            box, text="Case sensitive", variable=self.case_sensitive_var
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        box = ttk.LabelFrame(parent, text="Add Text", padding=8)
        box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Prefix:").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.prefix_var).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Label(box, text="Suffix:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(box, textvariable=self.suffix_var).grid(
            row=1, column=1, sticky="ew", padx=5, pady=4
        )

        box = ttk.LabelFrame(parent, text="Formatting", padding=8)
        box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Case:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            box,
            textvariable=self.case_var,
            state="readonly",
            values=("No change", "lower", "UPPER", "Title Case", "Sentence case")
        ).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(box, text="Spaces:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(
            box,
            textvariable=self.space_var,
            state="readonly",
            values=(
                "No change",
                "Spaces to _",
                "Spaces to -",
                "_ to spaces",
                "- to spaces"
            )
        ).grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        ttk.Label(box, text="Remove chars:").grid(row=2, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.remove_chars_var).grid(
            row=2, column=1, sticky="ew", padx=5
        )
        ttk.Checkbutton(
            box, text="Remove accents", variable=self.remove_accents_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        box = ttk.LabelFrame(parent, text="Numbering", padding=8)
        box.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Position:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            box,
            textvariable=self.number_mode_var,
            state="readonly",
            values=("None", "Prefix", "Suffix")
        ).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(box, text="Start:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Spinbox(
            box, from_=-999999, to=999999,
            textvariable=self.number_start_var, width=8
        ).grid(row=1, column=1, sticky="w", padx=5)

        ttk.Label(box, text="Step:").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(
            box, from_=1, to=999999,
            textvariable=self.number_step_var, width=8
        ).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(box, text="Padding:").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Spinbox(
            box, from_=1, to=12,
            textvariable=self.number_padding_var, width=8
        ).grid(row=3, column=1, sticky="w", padx=5)

        ttk.Label(box, text="Separator:").grid(row=4, column=0, sticky="w")
        ttk.Entry(
            box, textvariable=self.number_separator_var, width=8
        ).grid(row=4, column=1, sticky="w", padx=5)

        box = ttk.LabelFrame(parent, text="Extension", padding=8)
        box.grid(row=5, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Case:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            box,
            textvariable=self.extension_case_var,
            state="readonly",
            values=("No change", "lower", "UPPER")
        ).grid(row=0, column=1, sticky="ew", padx=5)

    def build_preview(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        ttk.Label(
            parent,
            text="Preview — review this before renaming",
            font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("old", "new", "folder", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree.heading("old", text="Current Name")
        self.tree.heading("new", text="New Name")
        self.tree.heading("folder", text="Original Folder")
        self.tree.heading("status", text="Status")

        self.tree.column("old", width=230)
        self.tree.column("new", width=230)
        self.tree.column("folder", width=330)
        self.tree.column("status", width=100, anchor="center")

        y = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        x = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y.grid(row=0, column=1, sticky="ns")
        x.grid(row=1, column=0, sticky="ew")

    def bind_preview_updates(self):
        variables = [
            self.find_var, self.replace_var, self.regex_var,
            self.case_sensitive_var, self.prefix_var, self.suffix_var,
            self.case_var, self.space_var, self.remove_chars_var,
            self.remove_accents_var, self.number_mode_var,
            self.number_start_var, self.number_step_var,
            self.number_padding_var, self.number_separator_var,
            self.extension_case_var
        ]
        for var in variables:
            var.trace_add("write", lambda *_: self.after_idle(self.refresh_preview))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose root folder")
        if folder:
            self.folder_var.set(folder)
            self.scan_folder()

    def scan_folder(self):
        text = self.folder_var.get().strip()
        if not text:
            return

        root = Path(text).expanduser()
        if not root.is_dir():
            return

        found = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if not self.include_hidden_var.get():
                try:
                    parts = path.relative_to(root).parts
                except ValueError:
                    parts = path.parts
                if any(part.startswith(".") for part in parts):
                    continue

            if self.extension_matches(path):
                found.append(path)

        self.files = sorted(found, key=lambda p: str(p).lower())
        self.refresh_preview()

    def extension_matches(self, path):
        text = self.extension_var.get().strip()
        if not text or text == "*":
            return True

        allowed = set()
        for item in text.split(","):
            item = item.strip().lower()
            if not item:
                continue
            if item.startswith("*."):
                item = item[1:]
            elif not item.startswith("."):
                item = "." + item
            allowed.add(item)

        return path.suffix.lower() in allowed

    def make_new_name(self, path, index):
        name = path.stem
        ext = path.suffix

        find_text = self.find_var.get()
        replace_text = self.replace_var.get()

        if find_text:
            if self.regex_var.get():
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                name = re.sub(find_text, replace_text, name, flags=flags)
            elif self.case_sensitive_var.get():
                name = name.replace(find_text, replace_text)
            else:
                name = re.sub(
                    re.escape(find_text),
                    lambda _m: replace_text,
                    name,
                    flags=re.IGNORECASE
                )

        chars = self.remove_chars_var.get()
        if chars:
            name = name.translate(str.maketrans("", "", chars))

        if self.remove_accents_var.get():
            normalized = unicodedata.normalize("NFKD", name)
            name = "".join(
                c for c in normalized if not unicodedata.combining(c)
            )

        spaces = self.space_var.get()
        if spaces == "Spaces to _":
            name = name.replace(" ", "_")
        elif spaces == "Spaces to -":
            name = name.replace(" ", "-")
        elif spaces == "_ to spaces":
            name = name.replace("_", " ")
        elif spaces == "- to spaces":
            name = name.replace("-", " ")

        case = self.case_var.get()
        if case == "lower":
            name = name.lower()
        elif case == "UPPER":
            name = name.upper()
        elif case == "Title Case":
            name = name.title()
        elif case == "Sentence case" and name:
            name = name[0].upper() + name[1:].lower()

        name = self.prefix_var.get() + name + self.suffix_var.get()

        mode = self.number_mode_var.get()
        if mode != "None":
            start = int(self.number_start_var.get())
            step = int(self.number_step_var.get())
            padding = max(1, int(self.number_padding_var.get()))
            number = start + index * step
            number_text = str(number).zfill(padding)
            sep = self.number_separator_var.get()

            if mode == "Prefix":
                name = number_text + sep + name
            elif mode == "Suffix":
                name = name + sep + number_text

        ext_case = self.extension_case_var.get()
        if ext_case == "lower":
            ext = ext.lower()
        elif ext_case == "UPPER":
            ext = ext.upper()

        return name.strip() + ext

    def refresh_preview(self):
        if not hasattr(self, "tree"):
            return

        self.tree.delete(*self.tree.get_children())

        proposed = []
        destination_counts = {}

        for index, path in enumerate(self.files):
            try:
                new_name = self.make_new_name(path, index)
                status = "READY"

                if not new_name:
                    status = "EMPTY"
                elif "/" in new_name or "\x00" in new_name:
                    status = "INVALID"
                elif new_name == path.name:
                    status = "UNCHANGED"

                destination = path.with_name(new_name)
                key = os.path.normcase(str(destination))
                destination_counts[key] = destination_counts.get(key, 0) + 1
                proposed.append((path, new_name, status, destination))

            except re.error:
                proposed.append((path, path.name, "BAD REGEX", path))
            except (ValueError, tk.TclError):
                proposed.append((path, path.name, "BAD NUMBER", path))

        source_set = {os.path.normcase(str(p)) for p in self.files}
        ready = 0

        for path, new_name, status, destination in proposed:
            key = os.path.normcase(str(destination))

            if status == "READY":
                if destination_counts.get(key, 0) > 1:
                    status = "DUPLICATE"
                elif destination.exists() and key not in source_set:
                    status = "EXISTS"

            if status == "READY":
                ready += 1

            self.tree.insert(
                "",
                "end",
                values=(path.name, new_name, str(path.parent), status)
            )

        self.status_var.set(
            f"{len(self.files)} file(s) found recursively — {ready} ready to rename."
        )

    def rename_files(self):
        if not self.files:
            messagebox.showinfo(
                "Nothing to rename",
                "Choose a root folder first."
            )
            return

        plan = []
        source_set = {os.path.normcase(str(p)) for p in self.files}
        destination_set = set()

        for index, source in enumerate(self.files):
            try:
                new_name = self.make_new_name(source, index)
            except Exception as exc:
                messagebox.showerror("Invalid settings", str(exc))
                return

            destination = source.with_name(new_name)

            if destination == source:
                continue

            key = os.path.normcase(str(destination))

            if key in destination_set:
                messagebox.showerror(
                    "Duplicate filename",
                    f"More than one file would become:\n{destination}"
                )
                return

            if destination.exists() and key not in source_set:
                messagebox.showerror(
                    "Filename already exists",
                    f"This file will NOT be overwritten:\n\n{destination}"
                )
                return

            destination_set.add(key)
            plan.append((source, destination))

        if not plan:
            messagebox.showinfo(
                "Nothing changed",
                "The current settings do not change any filenames."
            )
            return

        if not messagebox.askyesno(
            "Confirm recursive rename",
            f"Rename {len(plan)} file(s)?\n\n"
            "Files will remain in their original folders.\n"
            "Only the filenames will change.\n\n"
            "Existing files will NOT be overwritten."
        ):
            return

        temporary = []
        completed = []

        try:
            # First move every source to a unique temporary filename.
            # This permits safe swaps such as A.txt <-> B.txt.
            for source, destination in plan:
                temp = source.with_name(
                    f".__rename_{uuid.uuid4().hex}__{source.name}"
                )
                source.rename(temp)
                temporary.append((temp, destination, source))

            # Then give each temporary file its final filename.
            for temp, destination, original in temporary:
                final = temp.with_name(destination.name)
                temp.rename(final)
                completed.append((final, original))

        except Exception as exc:
            # Best-effort rollback.
            for current, original in reversed(completed):
                try:
                    if current.exists() and not original.exists():
                        current.rename(original)
                except OSError:
                    pass

            for temp, _destination, original in reversed(temporary):
                try:
                    if temp.exists() and not original.exists():
                        temp.rename(original)
                except OSError:
                    pass

            messagebox.showerror(
                "Rename failed",
                f"{exc}\n\nA rollback was attempted."
            )
            self.scan_folder()
            return

        self.last_rename = completed
        self.scan_folder()

        messagebox.showinfo(
            "Rename complete",
            f"Successfully renamed {len(completed)} file(s).\n\n"
            "All files stayed in their original folders."
        )

    def undo_last(self):
        if not self.last_rename:
            messagebox.showinfo(
                "Undo",
                "There is no rename batch to undo."
            )
            return

        restored = 0
        failures = []

        for current, original in reversed(self.last_rename):
            try:
                if not current.exists():
                    failures.append(f"Missing: {current}")
                elif original.exists():
                    failures.append(f"Already exists: {original}")
                else:
                    current.rename(original)
                    restored += 1
            except OSError as exc:
                failures.append(f"{current.name}: {exc}")

        self.last_rename = []
        self.scan_folder()

        if failures:
            messagebox.showwarning(
                "Undo partly completed",
                f"Restored {restored} file(s).\n\n" +
                "\n".join(failures[:10])
            )
        else:
            messagebox.showinfo(
                "Undo complete",
                f"Restored {restored} file(s)."
            )

    def reset_options(self):
        self.find_var.set("")
        self.replace_var.set("")
        self.regex_var.set(False)
        self.case_sensitive_var.set(False)
        self.prefix_var.set("")
        self.suffix_var.set("")
        self.case_var.set("No change")
        self.space_var.set("No change")
        self.remove_chars_var.set("")
        self.remove_accents_var.set(False)
        self.number_mode_var.set("None")
        self.number_start_var.set(1)
        self.number_step_var.set(1)
        self.number_padding_var.set(3)
        self.number_separator_var.set("_")
        self.extension_case_var.set("No change")
        self.refresh_preview()


if __name__ == "__main__":
    RecursiveRenamer().mainloop()
