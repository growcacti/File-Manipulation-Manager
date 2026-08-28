#!/usr/bin/env python3
import os
import re
import shutil
import unicodedata
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class BulkRenamer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Friendly Bulk File Renamer")
        self.geometry("1120x800")
        self.minsize(900, 650)

        self.items = []
        self.last_rename = []

        self._make_variables()
        self._make_style()
        self._build_gui()
        self._bind_variables()

    def _make_variables(self):
        self.folder_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=False)
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.extension_filter_var = tk.StringVar(value="*")

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

        # Safe/non-destructive output settings
        self.safe_copy_var = tk.BooleanVar(value=True)
        self.output_folder_var = tk.StringVar(value="Renamed_Output")

        self.status_var = tk.StringVar(value="Choose a folder or add files.")

    def _make_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("TkDefaultFont", 14, "bold"))
        style.configure(
            "Section.TLabelframe.Label",
            font=("TkDefaultFont", 10, "bold")
        )

    def _build_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(
            top,
            text="Friendly Bulk File Renamer",
            style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))

        ttk.Label(top, text="Folder:").grid(row=1, column=0, sticky="w")

        ttk.Entry(top, textvariable=self.folder_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=6
        )

        ttk.Button(
            top,
            text="Choose Folder...",
            command=self.choose_folder
        ).grid(row=1, column=3, padx=3)

        ttk.Button(
            top,
            text="Add Files...",
            command=self.add_files
        ).grid(row=1, column=4, padx=3)

        ttk.Checkbutton(
            top,
            text="Recursive",
            variable=self.recursive_var,
            command=self.load_folder
        ).grid(row=2, column=1, sticky="w", pady=(6, 0))

        ttk.Checkbutton(
            top,
            text="Include hidden items",
            variable=self.include_hidden_var,
            command=self.load_folder
        ).grid(row=2, column=2, sticky="w", pady=(6, 0))

        ttk.Label(top, text="Extensions:").grid(
            row=3, column=0, sticky="w", pady=(6, 0)
        )

        ttk.Entry(
            top,
            textvariable=self.extension_filter_var,
            width=30
        ).grid(row=3, column=1, sticky="w", padx=6, pady=(6, 0))

        ttk.Label(
            top,
            text="Examples:  *   .jpg   .jpg,.png,.txt"
        ).grid(row=3, column=2, columnspan=3, sticky="w", pady=(6, 0))

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew", padx=10)

        options = ttk.Frame(body, padding=(0, 0, 8, 0))
        preview = ttk.Frame(body)

        body.add(options, weight=0)
        body.add(preview, weight=1)

        self._build_options(options)
        self._build_preview(preview)

        bottom = ttk.Frame(self, padding=10)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        ttk.Label(bottom, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )

        ttk.Button(
            bottom,
            text="Refresh Preview",
            command=self.refresh_preview
        ).grid(row=0, column=1, padx=4)

        ttk.Button(
            bottom,
            text="Reset Options",
            command=self.reset_options
        ).grid(row=0, column=2, padx=4)

        ttk.Button(
            bottom,
            text="Undo Last Rename",
            command=self.undo_last
        ).grid(row=0, column=3, padx=4)

        ttk.Button(
            bottom,
            text="RUN",
            command=self.apply_changes
        ).grid(row=0, column=4, padx=(12, 0))

    def _build_options(self, parent):
        parent.columnconfigure(0, weight=1)

        safe_box = ttk.LabelFrame(
            parent,
            text="Safe Output Mode",
            style="Section.TLabelframe",
            padding=8
        )
        safe_box.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        safe_box.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            safe_box,
            text="Copy files and rename copies only",
            variable=self.safe_copy_var
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(safe_box, text="Output folder:").grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )

        ttk.Entry(
            safe_box,
            textvariable=self.output_folder_var
        ).grid(row=1, column=1, sticky="ew", padx=5, pady=(6, 0))

        ttk.Label(
            safe_box,
            text="Recommended: leave this checked to preserve originals."
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        replace_box = ttk.LabelFrame(
            parent,
            text="Find and Replace",
            style="Section.TLabelframe",
            padding=8
        )
        replace_box.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        replace_box.columnconfigure(1, weight=1)

        ttk.Label(replace_box, text="Find:").grid(row=0, column=0, sticky="w")
        ttk.Entry(replace_box, textvariable=self.find_var).grid(
            row=0, column=1, sticky="ew", padx=5
        )

        ttk.Label(replace_box, text="Replace:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(replace_box, textvariable=self.replace_var).grid(
            row=1, column=1, sticky="ew", padx=5, pady=4
        )

        ttk.Checkbutton(
            replace_box,
            text="Regular expression",
            variable=self.regex_var
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Checkbutton(
            replace_box,
            text="Case sensitive",
            variable=self.case_sensitive_var
        ).grid(row=3, column=0, columnspan=2, sticky="w")

        add_box = ttk.LabelFrame(
            parent,
            text="Add Text",
            style="Section.TLabelframe",
            padding=8
        )
        add_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        add_box.columnconfigure(1, weight=1)

        ttk.Label(add_box, text="Prefix:").grid(row=0, column=0, sticky="w")
        ttk.Entry(add_box, textvariable=self.prefix_var).grid(
            row=0, column=1, sticky="ew", padx=5
        )

        ttk.Label(add_box, text="Suffix:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(add_box, textvariable=self.suffix_var).grid(
            row=1, column=1, sticky="ew", padx=5, pady=4
        )

        format_box = ttk.LabelFrame(
            parent,
            text="Name Formatting",
            style="Section.TLabelframe",
            padding=8
        )
        format_box.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        format_box.columnconfigure(1, weight=1)

        ttk.Label(format_box, text="Case:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            format_box,
            textvariable=self.case_var,
            state="readonly",
            values=("No change", "lower", "UPPER", "Title Case", "Sentence case")
        ).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(format_box, text="Spaces:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Combobox(
            format_box,
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

        ttk.Label(format_box, text="Remove chars:").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(
            format_box,
            textvariable=self.remove_chars_var
        ).grid(row=2, column=1, sticky="ew", padx=5)

        ttk.Checkbutton(
            format_box,
            text="Remove accents",
            variable=self.remove_accents_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        number_box = ttk.LabelFrame(
            parent,
            text="Numbering",
            style="Section.TLabelframe",
            padding=8
        )
        number_box.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        number_box.columnconfigure(1, weight=1)

        ttk.Label(number_box, text="Position:").grid(
            row=0, column=0, sticky="w"
        )

        ttk.Combobox(
            number_box,
            textvariable=self.number_mode_var,
            state="readonly",
            values=("None", "Prefix", "Suffix")
        ).grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(number_box, text="Start:").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Spinbox(
            number_box,
            from_=-999999,
            to=999999,
            textvariable=self.number_start_var,
            width=9
        ).grid(row=1, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(number_box, text="Step:").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Spinbox(
            number_box,
            from_=1,
            to=999999,
            textvariable=self.number_step_var,
            width=9
        ).grid(row=2, column=1, sticky="w", padx=5)

        ttk.Label(number_box, text="Padding:").grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Spinbox(
            number_box,
            from_=1,
            to=12,
            textvariable=self.number_padding_var,
            width=9
        ).grid(row=3, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(number_box, text="Separator:").grid(
            row=4, column=0, sticky="w"
        )
        ttk.Entry(
            number_box,
            textvariable=self.number_separator_var,
            width=10
        ).grid(row=4, column=1, sticky="w", padx=5)

        ext_box = ttk.LabelFrame(
            parent,
            text="File Extension",
            style="Section.TLabelframe",
            padding=8
        )
        ext_box.grid(row=5, column=0, sticky="ew")
        ext_box.columnconfigure(1, weight=1)

        ttk.Label(ext_box, text="Extension case:").grid(
            row=0, column=0, sticky="w"
        )

        ttk.Combobox(
            ext_box,
            textvariable=self.extension_case_var,
            state="readonly",
            values=("No change", "lower", "UPPER")
        ).grid(row=0, column=1, sticky="ew", padx=5)

    def _build_preview(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ttk.Button(
            toolbar,
            text="Select All",
            command=self.select_all
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="Select None",
            command=self.select_none
        ).pack(side="left", padx=4)

        ttk.Button(
            toolbar,
            text="Remove Selected",
            command=self.remove_selected
        ).pack(side="left")

        tree_frame = ttk.Frame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("old", "new", "folder", "status")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        self.tree.heading("old", text="Current Name")
        self.tree.heading("new", text="New Name")
        self.tree.heading("folder", text="Folder")
        self.tree.heading("status", text="Status")

        self.tree.column("old", width=240, minwidth=120)
        self.tree.column("new", width=240, minwidth=120)
        self.tree.column("folder", width=300, minwidth=120)
        self.tree.column("status", width=110, minwidth=80, anchor="center")

        ybar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview
        )
        xbar = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=ybar.set,
            xscrollcommand=xbar.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

    def _bind_variables(self):
        variables = [
            self.find_var,
            self.replace_var,
            self.regex_var,
            self.case_sensitive_var,
            self.prefix_var,
            self.suffix_var,
            self.case_var,
            self.space_var,
            self.remove_chars_var,
            self.remove_accents_var,
            self.number_mode_var,
            self.number_start_var,
            self.number_step_var,
            self.number_padding_var,
            self.number_separator_var,
            self.extension_case_var,
            self.safe_copy_var,
            self.output_folder_var,
        ]

        for variable in variables:
            variable.trace_add(
                "write",
                lambda *_: self.after_idle(self.refresh_preview)
            )

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose folder")
        if not folder:
            return

        self.folder_var.set(folder)
        self.load_folder()

    def add_files(self):
        filenames = filedialog.askopenfilenames(title="Choose files")
        if not filenames:
            return

        existing = {str(p) for p in self.items}

        for name in filenames:
            p = Path(name)
            if str(p) not in existing:
                self.items.append(p)
                existing.add(str(p))

        self.items.sort(key=lambda p: str(p).lower())
        self.refresh_preview()

    def load_folder(self):
        folder_text = self.folder_var.get().strip()
        if not folder_text:
            return

        folder = Path(folder_text).expanduser()
        if not folder.is_dir():
            return

        iterator = folder.rglob("*") if self.recursive_var.get() else folder.iterdir()

        found = []

        for p in iterator:
            if not p.is_file():
                continue

            if not self.include_hidden_var.get():
                try:
                    parts = p.relative_to(folder).parts
                except ValueError:
                    parts = p.parts

                if any(part.startswith(".") for part in parts):
                    continue

            if self._extension_matches(p):
                found.append(p)

        self.items = sorted(found, key=lambda p: str(p).lower())
        self.refresh_preview()

    def _extension_matches(self, path):
        text = self.extension_filter_var.get().strip()

        if not text or text == "*":
            return True

        allowed = set()

        for part in text.split(","):
            part = part.strip().lower()

            if not part:
                continue

            if part.startswith("*."):
                part = part[1:]
            elif not part.startswith("."):
                part = "." + part

            allowed.add(part)

        return path.suffix.lower() in allowed

    def make_new_name(self, path, index):
        name = path.stem
        extension = path.suffix

        find_text = self.find_var.get()
        replace_text = self.replace_var.get()

        if find_text:
            if self.regex_var.get():
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                name = re.sub(find_text, replace_text, name, flags=flags)
            else:
                if self.case_sensitive_var.get():
                    name = name.replace(find_text, replace_text)
                else:
                    name = re.sub(
                        re.escape(find_text),
                        lambda _m: replace_text,
                        name,
                        flags=re.IGNORECASE
                    )

        remove_chars = self.remove_chars_var.get()
        if remove_chars:
            name = name.translate(
                str.maketrans("", "", remove_chars)
            )

        if self.remove_accents_var.get():
            normalized = unicodedata.normalize("NFKD", name)
            name = "".join(
                c for c in normalized
                if not unicodedata.combining(c)
            )

        space_mode = self.space_var.get()

        if space_mode == "Spaces to _":
            name = name.replace(" ", "_")
        elif space_mode == "Spaces to -":
            name = name.replace(" ", "-")
        elif space_mode == "_ to spaces":
            name = name.replace("_", " ")
        elif space_mode == "- to spaces":
            name = name.replace("-", " ")

        case_mode = self.case_var.get()

        if case_mode == "lower":
            name = name.lower()
        elif case_mode == "UPPER":
            name = name.upper()
        elif case_mode == "Title Case":
            name = name.title()
        elif case_mode == "Sentence case":
            if name:
                name = name[:1].upper() + name[1:].lower()

        name = self.prefix_var.get() + name + self.suffix_var.get()

        if self.number_mode_var.get() != "None":
            try:
                start = int(self.number_start_var.get())
                step = int(self.number_step_var.get())
                padding = max(1, int(self.number_padding_var.get()))
            except (tk.TclError, ValueError):
                start, step, padding = 1, 1, 3

            number = start + index * step
            number_text = str(number).zfill(padding)
            separator = self.number_separator_var.get()

            if self.number_mode_var.get() == "Prefix":
                name = number_text + separator + name
            elif self.number_mode_var.get() == "Suffix":
                name = name + separator + number_text

        if self.extension_case_var.get() == "lower":
            extension = extension.lower()
        elif self.extension_case_var.get() == "UPPER":
            extension = extension.upper()

        return (name.strip() + extension).strip()

    def refresh_preview(self):
        if not hasattr(self, "tree"):
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        seen = {}

        generated = []

        for index, path in enumerate(self.items):
            try:
                new_name = self.make_new_name(path, index)
                status = "READY"

                if not new_name:
                    status = "EMPTY NAME"

                if self.regex_var.get() and self.find_var.get():
                    re.compile(self.find_var.get())

            except re.error:
                new_name = path.name
                status = "BAD REGEX"
            except Exception:
                new_name = path.name
                status = "ERROR"

            generated.append((path, new_name, status))

            key = new_name.lower()
            seen[key] = seen.get(key, 0) + 1

        ready_count = 0

        for path, new_name, status in generated:
            if seen.get(new_name.lower(), 0) > 1:
                status = "DUPLICATE"

            if new_name == path.name:
                status = "UNCHANGED"

            if status == "READY":
                ready_count += 1

            self.tree.insert(
                "",
                "end",
                iid=str(path),
                values=(
                    path.name,
                    new_name,
                    str(path.parent),
                    status
                )
            )

        mode = (
            "SAFE COPY MODE"
            if self.safe_copy_var.get()
            else "RENAME ORIGINALS"
        )

        self.status_var.set(
            f"{len(self.items)} item(s) loaded — "
            f"{ready_count} ready — {mode}"
        )

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def select_none(self):
        self.tree.selection_remove(self.tree.selection())

    def remove_selected(self):
        selected = set(self.tree.selection())

        if not selected:
            return

        self.items = [
            p for p in self.items
            if str(p) not in selected
        ]

        self.refresh_preview()

    def apply_changes(self):
        if not self.items:
            messagebox.showinfo(
                "Nothing to process",
                "Choose a folder or add files first."
            )
            return

        if self.safe_copy_var.get():
            self.copy_and_rename()
        else:
            self.rename_originals()

    def copy_and_rename(self):
        output_name = self.output_folder_var.get().strip()

        if not output_name:
            messagebox.showerror(
                "Output folder required",
                "Enter a name for the output folder."
            )
            return

        output_path = Path(output_name)

        if output_path.is_absolute() or ".." in output_path.parts:
            messagebox.showerror(
                "Invalid output folder",
                "Use a simple folder name such as:\n\nRenamed_Output"
            )
            return

        if self.folder_var.get().strip():
            source_root = Path(
                self.folder_var.get().strip()
            ).expanduser()
        else:
            source_root = self.items[0].parent

        output_root = source_root / output_name

        try:
            output_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "Cannot create output folder",
                f"{exc}"
            )
            return

        copied = 0
        skipped = []

        for index, source in enumerate(self.items):
            try:
                new_name = self.make_new_name(source, index)

                if not new_name:
                    skipped.append(
                        f"{source.name}: empty new name"
                    )
                    continue

                try:
                    relative_parent = source.parent.relative_to(source_root)
                except ValueError:
                    relative_parent = Path()

                target_folder = output_root / relative_parent
                target_folder.mkdir(parents=True, exist_ok=True)

                destination = target_folder / new_name

                if destination.exists():
                    skipped.append(
                        f"{destination.name}: already exists"
                    )
                    continue

                # copy2 preserves timestamps and metadata where possible
                shutil.copy2(source, destination)
                copied += 1

            except Exception as exc:
                skipped.append(
                    f"{source.name}: {exc}"
                )

        if skipped:
            details = "\n".join(skipped[:12])

            if len(skipped) > 12:
                details += (
                    f"\n...and {len(skipped) - 12} more."
                )

            messagebox.showwarning(
                "Safe copy finished",
                f"Copied and renamed {copied} file(s).\n\n"
                f"Original files were NOT changed.\n\n"
                f"Output folder:\n{output_root}\n\n"
                f"Skipped:\n{details}"
            )
        else:
            messagebox.showinfo(
                "Safe copy complete",
                f"Copied and renamed {copied} file(s).\n\n"
                f"Original files were NOT changed.\n\n"
                f"Output folder:\n{output_root}"
            )

        self.status_var.set(
            f"Safe copy complete — {copied} file(s) created."
        )

    def rename_originals(self):
        plan = []

        for index, source in enumerate(self.items):
            try:
                new_name = self.make_new_name(source, index)
            except Exception as exc:
                messagebox.showerror(
                    "Rename error",
                    str(exc)
                )
                return

            destination = source.with_name(new_name)

            if destination == source:
                continue

            if destination.exists():
                messagebox.showerror(
                    "Name conflict",
                    f"Already exists:\n{destination}"
                )
                return

            plan.append((source, destination))

        if not plan:
            messagebox.showinfo(
                "Nothing changed",
                "No filenames would change."
            )
            return

        if not messagebox.askyesno(
            "Confirm rename",
            f"Rename {len(plan)} original file(s)?\n\n"
            "This changes the original filenames.\n\n"
            "For maximum safety, use Safe Output Mode instead."
        ):
            return

        temporary = []
        completed = []

        try:
            for source, destination in plan:
                temp = source.with_name(
                    f".__bulkrename_{uuid.uuid4().hex}__{source.name}"
                )
                source.rename(temp)
                temporary.append(
                    (temp, destination, source)
                )

            for temp, destination, original in temporary:
                final_destination = temp.with_name(destination.name)
                temp.rename(final_destination)
                completed.append(
                    (final_destination, original)
                )

        except Exception as exc:
            messagebox.showerror(
                "Rename failed",
                f"{exc}"
            )
            return

        self.last_rename = completed

        if self.folder_var.get():
            self.load_folder()
        else:
            self.items = [
                new for new, _old in completed
            ]
            self.refresh_preview()

        messagebox.showinfo(
            "Rename complete",
            f"Renamed {len(completed)} original file(s)."
        )

    def undo_last(self):
        if not self.last_rename:
            messagebox.showinfo(
                "Undo",
                "There is no original-file rename to undo.\n\n"
                "Safe copy mode does not alter originals."
            )
            return

        restored = 0

        for current, original in reversed(self.last_rename):
            try:
                if current.exists() and not original.exists():
                    current.rename(original)
                    restored += 1
            except OSError:
                pass

        self.last_rename = []

        if self.folder_var.get():
            self.load_folder()

        messagebox.showinfo(
            "Undo",
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

        # Reset to safest mode.
        self.safe_copy_var.set(True)
        self.output_folder_var.set("Renamed_Output")

        self.refresh_preview()


if __name__ == "__main__":
    app = BulkRenamer()
    app.mainloop()
