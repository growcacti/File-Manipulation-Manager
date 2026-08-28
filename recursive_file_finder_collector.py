import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


class FileFinderCollector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recursive File Finder and Collector")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.search_folders = []
        self.matches = []

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ---------------- Search folders ----------------
        folder_frame = ttk.LabelFrame(self, text="1. Folders to Search")
        folder_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        folder_frame.columnconfigure(0, weight=1)

        self.folder_list = tk.Listbox(folder_frame, height=4)
        self.folder_list.grid(row=0, column=0, rowspan=3, padx=8, pady=8, sticky="nsew")

        ttk.Button(folder_frame, text="Add Folder", command=self.add_folder).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(folder_frame, text="Remove Selected", command=self.remove_folder).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(folder_frame, text="Clear Folders", command=self.clear_folders).grid(
            row=2, column=1, padx=5, pady=5, sticky="ew"
        )

        # ---------------- Search options ----------------
        options = ttk.LabelFrame(self, text="2. Search Rules")
        options.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        for col in range(6):
            options.columnconfigure(col, weight=1 if col in (1, 3, 5) else 0)

        ttk.Label(options, text="Name contains:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.contains_var = tk.StringVar()
        ttk.Entry(options, textvariable=self.contains_var).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(options, text="Starts with:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.starts_var = tk.StringVar()
        ttk.Entry(options, textvariable=self.starts_var).grid(
            row=0, column=3, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(options, text="Ends with:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.ends_var = tk.StringVar()
        ttk.Entry(options, textvariable=self.ends_var).grid(
            row=0, column=5, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(options, text="Extension(s):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.extensions_var = tk.StringVar()
        ttk.Entry(options, textvariable=self.extensions_var).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )
        ttk.Label(
            options,
            text="Example: jpg,png,pdf or .jpg,.png",
        ).grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(options, text="Regex:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.regex_var = tk.StringVar()
        ttk.Entry(options, textvariable=self.regex_var).grid(
            row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        self.use_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options, text="Use regex", variable=self.use_regex_var
        ).grid(row=2, column=4, padx=5, pady=5, sticky="w")

        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options, text="Case sensitive", variable=self.case_sensitive_var
        ).grid(row=2, column=5, padx=5, pady=5, sticky="w")

        self.capital_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options,
            text="Filename contains uppercase letter",
            variable=self.capital_var,
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(options, text="Simple pattern:").grid(row=3, column=2, padx=5, pady=5, sticky="e")
        self.simple_pattern_var = tk.StringVar()
        self.simple_pattern_combo = ttk.Combobox(
            options,
            textvariable=self.simple_pattern_var,
            state="readonly",
            values=[
                "",
                "Contains digits",
                "Starts with digits",
                "Ends with digits",
                "Contains spaces",
                "Contains underscore",
                "Contains hyphen",
                "Contains parentheses",
                "All uppercase filename",
                "All lowercase filename",
            ],
        )
        self.simple_pattern_combo.grid(row=3, column=3, columnspan=2, padx=5, pady=5, sticky="ew")
        self.simple_pattern_combo.current(0)

        self.match_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options,
            text="Require ALL filled rules",
            variable=self.match_all_var,
        ).grid(row=3, column=5, padx=5, pady=5, sticky="w")

        # ---------------- Search controls ----------------
        controls = ttk.Frame(self)
        controls.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        controls.columnconfigure(5, weight=1)

        ttk.Button(controls, text="Search", command=self.search).grid(
            row=0, column=0, padx=3
        )
        ttk.Button(controls, text="Clear Results", command=self.clear_results).grid(
            row=0, column=1, padx=3
        )
        ttk.Button(controls, text="Select All", command=self.select_all).grid(
            row=0, column=2, padx=3
        )
        ttk.Button(controls, text="Select None", command=self.select_none).grid(
            row=0, column=3, padx=3
        )

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(controls, textvariable=self.status_var).grid(
            row=0, column=5, padx=8, sticky="e"
        )

        # ---------------- Results ----------------
        result_frame = ttk.LabelFrame(self, text="3. Matching Files")
        result_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        columns = ("name", "extension", "folder", "fullpath")
        self.tree = ttk.Treeview(
            result_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
        )

        self.tree.heading("name", text="File Name")
        self.tree.heading("extension", text="Extension")
        self.tree.heading("folder", text="Folder")
        self.tree.heading("fullpath", text="Full Path")

        self.tree.column("name", width=220)
        self.tree.column("extension", width=80, anchor="center")
        self.tree.column("folder", width=250)
        self.tree.column("fullpath", width=450)

        yscroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(result_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        # ---------------- Copy / Move ----------------
        action_frame = ttk.LabelFrame(self, text="4. Copy or Move Selected Files")
        action_frame.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")
        action_frame.columnconfigure(1, weight=1)

        ttk.Label(action_frame, text="Destination:").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )
        self.dest_var = tk.StringVar()
        ttk.Entry(action_frame, textvariable=self.dest_var).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )
        ttk.Button(action_frame, text="Browse", command=self.choose_destination).grid(
            row=0, column=2, padx=5, pady=5
        )

        self.auto_folder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            action_frame,
            text="Create a new collection subfolder automatically",
            variable=self.auto_folder_var,
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Button(action_frame, text="Copy Selected", command=lambda: self.transfer("copy")).grid(
            row=1, column=2, padx=5, pady=5
        )
        ttk.Button(action_frame, text="Move Selected", command=lambda: self.transfer("move")).grid(
            row=1, column=3, padx=5, pady=5
        )

    def add_folder(self):
        folder = filedialog.askdirectory(title="Choose folder to search")
        if folder and folder not in self.search_folders:
            self.search_folders.append(folder)
            self.folder_list.insert(tk.END, folder)

    def remove_folder(self):
        selected = list(self.folder_list.curselection())
        for index in reversed(selected):
            self.search_folders.pop(index)
            self.folder_list.delete(index)

    def clear_folders(self):
        self.search_folders.clear()
        self.folder_list.delete(0, tk.END)

    def clear_results(self):
        self.matches.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_var.set("Results cleared")

    def select_all(self):
        items = self.tree.get_children()
        self.tree.selection_set(items)

    def select_none(self):
        self.tree.selection_remove(self.tree.selection())

    def choose_destination(self):
        folder = filedialog.askdirectory(title="Choose destination folder")
        if folder:
            self.dest_var.set(folder)

    def normalize_extensions(self):
        text = self.extensions_var.get().strip()
        if not text:
            return []

        extensions = []
        for ext in text.split(","):
            ext = ext.strip()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            extensions.append(ext if self.case_sensitive_var.get() else ext.lower())
        return extensions

    def simple_pattern_match(self, filename):
        pattern = self.simple_pattern_var.get()
        stem = Path(filename).stem

        if not pattern:
            return True
        if pattern == "Contains digits":
            return bool(re.search(r"\d", filename))
        if pattern == "Starts with digits":
            return bool(re.match(r"^\d", filename))
        if pattern == "Ends with digits":
            return bool(re.search(r"\d(?=\.[^.]+$|$)", filename))
        if pattern == "Contains spaces":
            return " " in filename
        if pattern == "Contains underscore":
            return "_" in filename
        if pattern == "Contains hyphen":
            return "-" in filename
        if pattern == "Contains parentheses":
            return "(" in filename or ")" in filename
        if pattern == "All uppercase filename":
            letters = [c for c in stem if c.isalpha()]
            return bool(letters) and all(c.isupper() for c in letters)
        if pattern == "All lowercase filename":
            letters = [c for c in stem if c.isalpha()]
            return bool(letters) and all(c.islower() for c in letters)

        return True

    def filename_matches(self, filename):
        case_sensitive = self.case_sensitive_var.get()

        name_for_compare = filename if case_sensitive else filename.lower()
        contains = self.contains_var.get().strip()
        starts = self.starts_var.get().strip()
        ends = self.ends_var.get().strip()

        if not case_sensitive:
            contains = contains.lower()
            starts = starts.lower()
            ends = ends.lower()

        rules = []

        if contains:
            rules.append(contains in name_for_compare)

        if starts:
            rules.append(name_for_compare.startswith(starts))

        if ends:
            rules.append(name_for_compare.endswith(ends))

        extensions = self.normalize_extensions()
        if extensions:
            suffix = Path(filename).suffix
            suffix_cmp = suffix if case_sensitive else suffix.lower()
            rules.append(suffix_cmp in extensions)

        if self.capital_var.get():
            rules.append(any(ch.isupper() for ch in Path(filename).stem))

        if self.simple_pattern_var.get():
            rules.append(self.simple_pattern_match(filename))

        if self.use_regex_var.get():
            regex_text = self.regex_var.get().strip()
            if regex_text:
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    rules.append(bool(re.search(regex_text, filename, flags)))
                except re.error as exc:
                    raise ValueError(f"Invalid regular expression:\n{exc}")

        # If no rules are filled, match everything.
        if not rules:
            return True

        return all(rules) if self.match_all_var.get() else any(rules)

    def search(self):
        if not self.search_folders:
            messagebox.showwarning("No folders", "Add at least one folder to search.")
            return

        self.clear_results()
        self.status_var.set("Searching...")
        self.update_idletasks()

        found = []
        seen = set()

        try:
            for root_folder in self.search_folders:
                for root, dirs, files in os.walk(root_folder):
                    for filename in files:
                        if self.filename_matches(filename):
                            full_path = os.path.abspath(os.path.join(root, filename))
                            if full_path in seen:
                                continue
                            seen.add(full_path)
                            found.append(full_path)
        except ValueError as exc:
            messagebox.showerror("Search error", str(exc))
            self.status_var.set("Search error")
            return
        except PermissionError as exc:
            messagebox.showwarning(
                "Permission problem",
                f"A folder could not be accessed:\n{exc}"
            )

        self.matches = found

        for path_text in found:
            p = Path(path_text)
            self.tree.insert(
                "",
                tk.END,
                values=(p.name, p.suffix, str(p.parent), str(p)),
            )

        self.status_var.set(f"{len(found)} matching file(s) found")

    def selected_paths(self):
        selected = self.tree.selection()
        paths = []

        for item in selected:
            values = self.tree.item(item, "values")
            if values:
                paths.append(values[3])

        return paths

    def unique_destination_path(self, destination_folder, filename):
        destination_folder = Path(destination_folder)
        target = destination_folder / filename

        if not target.exists():
            return target

        stem = target.stem
        suffix = target.suffix
        counter = 1

        while True:
            candidate = destination_folder / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def transfer(self, mode):
        paths = self.selected_paths()

        if not paths:
            messagebox.showwarning(
                "Nothing selected",
                "Select one or more matching files first."
            )
            return

        destination = self.dest_var.get().strip()
        if not destination:
            messagebox.showwarning(
                "No destination",
                "Choose a destination folder."
            )
            return

        destination = Path(destination)

        try:
            destination.mkdir(parents=True, exist_ok=True)

            if self.auto_folder_var.get():
                folder_name = "Collected_Files"
                collection_folder = destination / folder_name

                counter = 1
                while collection_folder.exists():
                    collection_folder = destination / f"{folder_name}_{counter}"
                    counter += 1

                collection_folder.mkdir(parents=True)
                destination = collection_folder

            completed = 0
            errors = []

            for source_text in paths:
                source = Path(source_text)

                if not source.exists():
                    errors.append(f"Missing: {source}")
                    continue

                target = self.unique_destination_path(destination, source.name)

                try:
                    if mode == "copy":
                        shutil.copy2(source, target)
                    else:
                        shutil.move(str(source), str(target))
                    completed += 1
                except Exception as exc:
                    errors.append(f"{source}\n{exc}")

            action = "Copied" if mode == "copy" else "Moved"

            message = f"{action} {completed} file(s) to:\n{destination}"

            if errors:
                message += f"\n\n{len(errors)} file(s) had errors."

            messagebox.showinfo("Finished", message)

            if mode == "move":
                self.search()

        except Exception as exc:
            messagebox.showerror("Transfer error", str(exc))


if __name__ == "__main__":
    app = FileFinderCollector()
    app.mainloop()
