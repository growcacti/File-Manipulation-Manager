#!/usr/bin/env python3
"""
Folder Housekeeper
------------------
Scan a directory recursively and report:
- Empty folders
- Non-empty folders
- Direct item count
- Recursive file count
- Recursive subfolder count
- Recursive folder size

Selected empty folders can be deleted after confirmation.

Uses only the Python standard library.
"""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def human_size(num_bytes):
    """Return a human-readable file size."""
    size = float(num_bytes)
    units = ("B", "KB", "MB", "GB", "TB", "PB")

    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0


class FolderInfo:
    def __init__(
        self,
        path,
        direct_items=0,
        file_count=0,
        folder_count=0,
        total_size=0,
        is_empty=False,
        error=""
    ):
        self.path = Path(path)
        self.direct_items = direct_items
        self.file_count = file_count
        self.folder_count = folder_count
        self.total_size = total_size
        self.is_empty = is_empty
        self.error = error


class FolderHousekeeper(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Folder Housekeeper")
        self.geometry("1120x720")
        self.minsize(900, 560)

        self.folder_results = []
        self.scan_thread = None

        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Choose a folder to scan.")
        self.summary_var = tk.StringVar(value="No scan has been run.")
        self.include_root_var = tk.BooleanVar(value=False)

        self._build_gui()

    def _build_gui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # -------------------------
        # Folder selection
        # -------------------------
        top = ttk.LabelFrame(self, text="Folder to scan")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Directory:").grid(
            row=0, column=0, padx=(8, 5), pady=8, sticky="w"
        )

        ttk.Entry(top, textvariable=self.path_var).grid(
            row=0, column=1, padx=5, pady=8, sticky="ew"
        )

        ttk.Button(top, text="Browse...", command=self.choose_folder).grid(
            row=0, column=2, padx=5, pady=8
        )

        self.scan_button = ttk.Button(
            top, text="Scan Folders", command=self.start_scan
        )
        self.scan_button.grid(row=0, column=3, padx=(5, 8), pady=8)

        ttk.Checkbutton(
            top,
            text="Include selected root folder in results",
            variable=self.include_root_var
        ).grid(
            row=1, column=1, columnspan=3, padx=5, pady=(0, 8), sticky="w"
        )

        # -------------------------
        # Summary
        # -------------------------
        summary = ttk.Frame(self)
        summary.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        summary.columnconfigure(0, weight=1)

        ttk.Label(
            summary,
            textvariable=self.summary_var,
            font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.progress = ttk.Progressbar(summary, mode="indeterminate", length=180)
        self.progress.grid(row=0, column=1, padx=(10, 0), sticky="e")

        # -------------------------
        # Notebook
        # -------------------------
        notebook = ttk.Notebook(self)
        notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        self.empty_tab = ttk.Frame(notebook)
        self.all_tab = ttk.Frame(notebook)

        notebook.add(self.empty_tab, text="Empty Folders")
        notebook.add(self.all_tab, text="All Folders")

        self.empty_tree = self._make_tree(
            self.empty_tab,
            columns=("path",),
            headings=("Empty Folder",),
            widths=(850,)
        )

        self.all_tree = self._make_tree(
            self.all_tab,
            columns=(
                "status",
                "path",
                "direct",
                "files",
                "folders",
                "size"
            ),
            headings=(
                "Status",
                "Folder",
                "Direct Items",
                "Files",
                "Subfolders",
                "Size"
            ),
            widths=(90, 560, 90, 80, 90, 100)
        )

        # -------------------------
        # Controls
        # -------------------------
        controls = ttk.Frame(self)
        controls.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
        controls.columnconfigure(4, weight=1)

        ttk.Button(
            controls,
            text="Select All Empty",
            command=self.select_all_empty
        ).grid(row=0, column=0, padx=(0, 5))

        ttk.Button(
            controls,
            text="Clear Selection",
            command=self.clear_empty_selection
        ).grid(row=0, column=1, padx=5)

        self.delete_button = ttk.Button(
            controls,
            text="Delete Selected Empty Folders",
            command=self.delete_selected_empty
        )
        self.delete_button.grid(row=0, column=2, padx=5)

        ttk.Button(
            controls,
            text="Export Report...",
            command=self.export_report
        ).grid(row=0, column=3, padx=5)

        # -------------------------
        # Status bar
        # -------------------------
        status = ttk.Label(
            self,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w"
        )
        status.grid(row=4, column=0, sticky="ew", padx=10, pady=(5, 10))

    def _make_tree(self, parent, columns, headings, widths):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=60, anchor="w")

        yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)

        tree.configure(
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set
        )

        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        return tree

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose folder to scan")
        if folder:
            self.path_var.set(folder)

    def start_scan(self):
        root_text = self.path_var.get().strip()

        if not root_text:
            messagebox.showwarning(
                "No folder selected",
                "Choose a folder before scanning."
            )
            return

        root = Path(root_text)

        if not root.exists() or not root.is_dir():
            messagebox.showerror(
                "Invalid folder",
                "The selected folder does not exist or is not a directory."
            )
            return

        if self.scan_thread and self.scan_thread.is_alive():
            return

        self.folder_results.clear()
        self.empty_tree.delete(*self.empty_tree.get_children())
        self.all_tree.delete(*self.all_tree.get_children())

        self.scan_button.configure(state="disabled")
        self.delete_button.configure(state="disabled")
        self.progress.start(10)

        self.status_var.set(f"Scanning: {root}")
        self.summary_var.set("Scanning folders...")

        include_root = self.include_root_var.get()

        self.scan_thread = threading.Thread(
            target=self._scan_worker,
            args=(root, include_root),
            daemon=True
        )
        self.scan_thread.start()

    def _scan_worker(self, root, include_root):
        results = []
        errors = []

        try:
            # Bottom-up traversal lets us know all descendant sizes/counts.
            for current_dir, dirnames, filenames in os.walk(
                root,
                topdown=False,
                followlinks=False
            ):
                current_path = Path(current_dir)

                if current_path == root and not include_root:
                    continue

                total_size = 0
                file_count = 0
                folder_count = 0
                error_text = ""

                try:
                    for walk_dir, subdirs, files in os.walk(
                        current_path,
                        topdown=True,
                        followlinks=False
                    ):
                        folder_count += len(subdirs)

                        for filename in files:
                            file_path = Path(walk_dir) / filename
                            try:
                                # Do not follow symlinks for size.
                                if file_path.is_symlink():
                                    continue
                                total_size += file_path.stat().st_size
                                file_count += 1
                            except (OSError, PermissionError):
                                pass

                    try:
                        direct_items = len(list(os.scandir(current_path)))
                    except (OSError, PermissionError) as exc:
                        direct_items = 0
                        error_text = str(exc)

                    # Truly empty means there are no entries at all.
                    is_empty = direct_items == 0 and not error_text

                    results.append(
                        FolderInfo(
                            path=current_path,
                            direct_items=direct_items,
                            file_count=file_count,
                            folder_count=folder_count,
                            total_size=total_size,
                            is_empty=is_empty,
                            error=error_text
                        )
                    )

                except (OSError, PermissionError) as exc:
                    errors.append(f"{current_path}: {exc}")

        except Exception as exc:
            errors.append(str(exc))

        results.sort(key=lambda item: str(item.path).lower())

        self.after(0, self._scan_complete, results, errors)

    def _scan_complete(self, results, errors):
        self.progress.stop()
        self.scan_button.configure(state="normal")
        self.delete_button.configure(state="normal")

        self.folder_results = results

        empty_count = 0
        nonempty_count = 0
        total_bytes = 0

        for info in results:
            if info.is_empty:
                empty_count += 1
                self.empty_tree.insert(
                    "",
                    "end",
                    values=(str(info.path),)
                )
                status = "EMPTY"
            elif info.error:
                status = "ERROR"
            else:
                nonempty_count += 1
                status = "Has files"

            total_bytes += info.total_size

            self.all_tree.insert(
                "",
                "end",
                values=(
                    status,
                    str(info.path),
                    info.direct_items,
                    info.file_count,
                    info.folder_count,
                    human_size(info.total_size)
                )
            )

        self.summary_var.set(
            f"Folders scanned: {len(results):,}    "
            f"Empty: {empty_count:,}    "
            f"Non-empty: {nonempty_count:,}    "
            f"Combined reported size: {human_size(total_bytes)}"
        )

        if errors:
            self.status_var.set(
                f"Scan finished with {len(errors)} access/error message(s)."
            )
        else:
            self.status_var.set("Scan finished.")

    def select_all_empty(self):
        items = self.empty_tree.get_children()
        self.empty_tree.selection_set(items)

    def clear_empty_selection(self):
        self.empty_tree.selection_remove(
            self.empty_tree.selection()
        )

    def delete_selected_empty(self):
        selected = self.empty_tree.selection()

        if not selected:
            messagebox.showinfo(
                "Nothing selected",
                "Select one or more empty folders first."
            )
            return

        paths = [
            Path(self.empty_tree.item(item, "values")[0])
            for item in selected
        ]

        preview = "\n".join(str(path) for path in paths[:12])
        if len(paths) > 12:
            preview += f"\n...and {len(paths) - 12} more."

        answer = messagebox.askyesno(
            "Delete empty folders?",
            "Only folders that are STILL empty will be removed.\n\n"
            f"Selected: {len(paths)}\n\n"
            f"{preview}\n\n"
            "Continue?"
        )

        if not answer:
            return

        deleted = 0
        skipped = 0
        failed = []

        # Deepest paths first, because deleting a child can make a parent empty.
        paths.sort(key=lambda p: len(p.parts), reverse=True)

        for path in paths:
            try:
                # os.rmdir is deliberately used because it refuses
                # to delete a non-empty directory.
                os.rmdir(path)
                deleted += 1
            except OSError as exc:
                skipped += 1
                failed.append(f"{path}: {exc}")

        message = (
            f"Deleted: {deleted}\n"
            f"Skipped/failed: {skipped}"
        )

        if failed:
            message += (
                "\n\nA folder may have become non-empty, be protected, "
                "or have a permissions problem."
            )

        messagebox.showinfo("Delete complete", message)

        # Rescan to update the display.
        self.start_scan()

    def export_report(self):
        if not self.folder_results:
            messagebox.showinfo(
                "No report",
                "Run a scan before exporting."
            )
            return

        filename = filedialog.asksaveasfilename(
            title="Save folder report",
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ],
            initialfile="folder_housekeeping_report.csv"
        )

        if not filename:
            return

        import csv

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "Status",
                    "Folder",
                    "Direct Items",
                    "Recursive Files",
                    "Recursive Subfolders",
                    "Size Bytes",
                    "Human Size",
                    "Error"
                ])

                for info in self.folder_results:
                    if info.is_empty:
                        status = "EMPTY"
                    elif info.error:
                        status = "ERROR"
                    else:
                        status = "HAS FILES"

                    writer.writerow([
                        status,
                        str(info.path),
                        info.direct_items,
                        info.file_count,
                        info.folder_count,
                        info.total_size,
                        human_size(info.total_size),
                        info.error
                    ])

            messagebox.showinfo(
                "Report saved",
                f"Report saved to:\n{filename}"
            )

        except OSError as exc:
            messagebox.showerror(
                "Could not save report",
                str(exc)
            )


if __name__ == "__main__":
    app = FolderHousekeeper()
    app.mainloop()
