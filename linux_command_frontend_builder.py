#!/usr/bin/env python3

import json
import os
import shlex
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path


APP_TITLE = "Linux Command Frontend Builder"
COMMAND_FILE = Path.home() / ".linux_command_frontend_commands.json"


DEFAULT_COMMANDS = {
    "Create Symlink": {
        "template": 'ln -s "{source}" "{destination}"',
        "needs_admin": False,
        "description": "Create a symbolic link from source to destination."
    },
    "Copy File/Folder": {
        "template": 'cp -rv "{source}" "{destination}"',
        "needs_admin": False,
        "description": "Copy a file or folder recursively."
    },
    "Move File/Folder": {
        "template": 'mv -v "{source}" "{destination}"',
        "needs_admin": False,
        "description": "Move or rename a file or folder."
    },
    "Rsync Copy": {
        "template": 'rsync -avh --progress "{source}" "{destination}"',
        "needs_admin": False,
        "description": "Copy with rsync while preserving attributes and showing progress."
    },
    "List Source": {
        "template": 'ls -lah "{source}"',
        "needs_admin": False,
        "description": "Show a detailed directory listing."
    },
    "Disk Usage Source": {
        "template": 'du -sh "{source}"',
        "needs_admin": False,
        "description": "Show total disk space used by the source."
    },
    "Delete Empty Folders": {
        "template": 'find "{source}" -type d -empty -delete',
        "needs_admin": False,
        "description": "Recursively delete empty folders below the selected source."
    },
    "chmod 777 Recursive": {
        "template": 'chmod -R 777 "{source}"',
        "needs_admin": True,
        "description": "Recursively give read/write/execute permissions to everyone."
    },
    "chmod User Read/Write": {
        "template": 'chmod -R u+rwX "{source}"',
        "needs_admin": True,
        "description": "Give the owner read/write access and directory execute access."
    },
    "Change Owner to Current User": {
        "template": 'chown -R {username}:{username} "{source}"',
        "needs_admin": True,
        "description": "Change ownership recursively to your current Linux user."
    },
    "Unmount Source": {
        "template": 'umount "{source}"',
        "needs_admin": True,
        "description": "Unmount the selected mount point or device."
    },
}


class LinuxCommandFrontend:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1080x780")
        self.root.minsize(850, 620)

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.command_name_var = tk.StringVar()
        self.command_template_var = tk.StringVar()
        self.rendered_command_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.admin_var = tk.BooleanVar(value=False)
        self.username = os.environ.get("USER", "")

        self.commands = self.load_commands()

        self.build_gui()
        self.populate_command_list()

        if self.commands:
            first = next(iter(self.commands))
            self.command_combo.set(first)
            self.load_selected_command()

    # ---------------------------------------------------------
    # GUI
    # ---------------------------------------------------------
    def build_gui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(11, weight=1)

        pad = {"padx": 6, "pady": 6}

        ttk.Label(
            self.root,
            text="Linux Command Frontend Builder",
            font=("TkDefaultFont", 16, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", **pad)

        ttk.Label(
            self.root,
            text="Choose paths with buttons, select or build a command, preview it, then run it."
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 8))

        # Source
        ttk.Label(self.root, text="Source:").grid(
            row=2, column=0, sticky="w", **pad
        )

        ttk.Entry(
            self.root,
            textvariable=self.source_var
        ).grid(row=2, column=1, sticky="ew", **pad)

        ttk.Button(
            self.root,
            text="File",
            command=self.choose_source_file
        ).grid(row=2, column=2, **pad)

        ttk.Button(
            self.root,
            text="Folder",
            command=self.choose_source_folder
        ).grid(row=2, column=3, **pad)

        # Destination
        ttk.Label(self.root, text="Destination:").grid(
            row=3, column=0, sticky="w", **pad
        )

        ttk.Entry(
            self.root,
            textvariable=self.destination_var
        ).grid(row=3, column=1, sticky="ew", **pad)

        ttk.Button(
            self.root,
            text="File",
            command=self.choose_destination_file
        ).grid(row=3, column=2, **pad)

        ttk.Button(
            self.root,
            text="Folder",
            command=self.choose_destination_folder
        ).grid(row=3, column=3, **pad)

        # Command selection
        ttk.Label(self.root, text="Saved Command:").grid(
            row=4, column=0, sticky="w", **pad
        )

        self.command_combo = ttk.Combobox(
            self.root,
            textvariable=self.command_name_var,
            state="readonly"
        )
        self.command_combo.grid(
            row=4, column=1, columnspan=2, sticky="ew", **pad
        )
        self.command_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.load_selected_command()
        )

        ttk.Button(
            self.root,
            text="Delete",
            command=self.delete_command
        ).grid(row=4, column=3, **pad)

        # Description
        ttk.Label(self.root, text="Description:").grid(
            row=5, column=0, sticky="nw", **pad
        )

        ttk.Label(
            self.root,
            textvariable=self.description_var,
            wraplength=760
        ).grid(row=5, column=1, columnspan=3, sticky="w", **pad)

        # Command template
        ttk.Label(self.root, text="Command Template:").grid(
            row=6, column=0, sticky="nw", **pad
        )

        self.command_entry = ttk.Entry(
            self.root,
            textvariable=self.command_template_var
        )
        self.command_entry.grid(
            row=6, column=1, columnspan=3, sticky="ew", **pad
        )
        self.command_entry.bind("<KeyRelease>", lambda event: self.update_preview())

        ttk.Label(
            self.root,
            text='Placeholders: {source}  {destination}  {username}'
        ).grid(row=7, column=1, columnspan=3, sticky="w", padx=6)

        ttk.Checkbutton(
            self.root,
            text="Run with administrator privileges (pkexec)",
            variable=self.admin_var,
            command=self.update_preview
        ).grid(row=8, column=1, columnspan=3, sticky="w", padx=6, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.grid(
            row=9, column=0, columnspan=4, sticky="ew", padx=6, pady=10
        )

        buttons = [
            ("Preview", self.update_preview),
            ("Run Command", self.run_command),
            ("Save As New", self.save_new_command),
            ("Update Selected", self.update_saved_command),
            ("Clear Output", self.clear_output),
        ]

        for col, (text, command) in enumerate(buttons):
            ttk.Button(
                button_frame,
                text=text,
                command=command
            ).grid(row=0, column=col, padx=4)

        # Preview
        ttk.Label(self.root, text="Command Preview:").grid(
            row=10, column=0, sticky="nw", **pad
        )

        self.preview_entry = ttk.Entry(
            self.root,
            textvariable=self.rendered_command_var,
            state="readonly"
        )
        self.preview_entry.grid(
            row=10, column=1, columnspan=3, sticky="ew", **pad
        )

        # Output
        output_frame = ttk.Frame(self.root)
        output_frame.grid(
            row=11, column=0, columnspan=4,
            sticky="nsew", padx=6, pady=6
        )
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)

        self.output_text = tk.Text(
            output_frame,
            wrap="word",
            height=18
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            output_frame,
            orient="vertical",
            command=self.output_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.source_var.trace_add("write", lambda *args: self.update_preview())
        self.destination_var.trace_add("write", lambda *args: self.update_preview())

    # ---------------------------------------------------------
    # File dialogs
    # ---------------------------------------------------------
    def choose_source_file(self):
        path = filedialog.askopenfilename(title="Select Source File")
        if path:
            self.source_var.set(path)

    def choose_source_folder(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_var.set(path)

    def choose_destination_file(self):
        path = filedialog.asksaveasfilename(title="Select Destination File")
        if path:
            self.destination_var.set(path)

    def choose_destination_folder(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.destination_var.set(path)

    # ---------------------------------------------------------
    # Command storage
    # ---------------------------------------------------------
    def load_commands(self):
        commands = dict(DEFAULT_COMMANDS)

        if COMMAND_FILE.exists():
            try:
                with COMMAND_FILE.open("r", encoding="utf-8") as f:
                    saved = json.load(f)

                if isinstance(saved, dict):
                    for name, value in saved.items():
                        if isinstance(value, str):
                            commands[name] = {
                                "template": value,
                                "needs_admin": False,
                                "description": "Custom saved command."
                            }
                        elif isinstance(value, dict):
                            commands[name] = {
                                "template": value.get("template", ""),
                                "needs_admin": bool(value.get("needs_admin", False)),
                                "description": value.get("description", "Custom saved command.")
                            }
            except Exception:
                pass

        return commands

    def save_commands_to_disk(self):
        try:
            with COMMAND_FILE.open("w", encoding="utf-8") as f:
                json.dump(self.commands, f, indent=4)
        except Exception as e:
            messagebox.showerror(
                "Save Error",
                f"Could not save commands:\n{e}"
            )

    def populate_command_list(self):
        self.command_combo["values"] = list(self.commands.keys())

    def load_selected_command(self):
        name = self.command_name_var.get()

        if name in self.commands:
            data = self.commands[name]
            self.command_template_var.set(data["template"])
            self.admin_var.set(data.get("needs_admin", False))
            self.description_var.set(data.get("description", ""))
            self.update_preview()

    def save_new_command(self):
        template = self.command_template_var.get().strip()

        if not template:
            messagebox.showwarning(
                "Missing Command",
                "Enter a command template first."
            )
            return

        name = simpledialog.askstring(
            "Command Name",
            "Enter a name for this command:"
        )

        if not name:
            return

        name = name.strip()

        description = simpledialog.askstring(
            "Description",
            "Enter a short description (optional):"
        ) or "Custom saved command."

        if name in self.commands:
            overwrite = messagebox.askyesno(
                "Command Exists",
                f'"{name}" already exists.\n\nOverwrite it?'
            )
            if not overwrite:
                return

        self.commands[name] = {
            "template": template,
            "needs_admin": self.admin_var.get(),
            "description": description
        }

        self.save_commands_to_disk()
        self.populate_command_list()
        self.command_combo.set(name)
        self.description_var.set(description)

    def update_saved_command(self):
        name = self.command_name_var.get()
        template = self.command_template_var.get().strip()

        if not name:
            messagebox.showwarning(
                "No Command Selected",
                "Select a saved command first."
            )
            return

        if not template:
            messagebox.showwarning(
                "Missing Command",
                "Enter a command template first."
            )
            return

        self.commands[name] = {
            "template": template,
            "needs_admin": self.admin_var.get(),
            "description": self.description_var.get() or "Saved command."
        }

        self.save_commands_to_disk()

        messagebox.showinfo(
            "Command Updated",
            f'"{name}" was updated.'
        )

    def delete_command(self):
        name = self.command_name_var.get()

        if not name:
            return

        if not messagebox.askyesno(
            "Delete Command",
            f'Delete "{name}"?'
        ):
            return

        if name in self.commands:
            del self.commands[name]

        self.save_commands_to_disk()
        self.populate_command_list()

        self.command_name_var.set("")
        self.command_template_var.set("")
        self.description_var.set("")
        self.rendered_command_var.set("")

    # ---------------------------------------------------------
    # Command preparation
    # ---------------------------------------------------------
    def make_command(self):
        template = self.command_template_var.get().strip()
        source = self.source_var.get().strip()
        destination = self.destination_var.get().strip()

        if not template:
            raise ValueError("No command template has been entered.")

        try:
            command = template.format(
                source=source,
                destination=destination,
                username=self.username
            )
        except KeyError as e:
            raise ValueError(
                f"Unknown placeholder in command: {e}\n\n"
                "Use only {source}, {destination}, and {username}."
            )

        return command

    def update_preview(self):
        try:
            command = self.make_command()
        except Exception:
            command = self.command_template_var.get()

        if self.admin_var.get() and command:
            shown = f"pkexec sh -c {shlex.quote(command)}"
        else:
            shown = command

        self.rendered_command_var.set(shown)

    # ---------------------------------------------------------
    # Command execution
    # ---------------------------------------------------------
    def run_command(self):
        try:
            command = self.make_command()
        except ValueError as e:
            messagebox.showerror("Command Error", str(e))
            return

        if not command:
            return

        # Extra warning for destructive commands
        destructive_words = ("rm ", " -delete", "chmod -R 777", "chown -R")
        if any(word in command for word in destructive_words):
            confirm_text = (
                "This command can make significant changes.\n\n"
                f"{command}\n\n"
                "Are you sure you want to continue?"
            )
        else:
            confirm_text = f"Run this command?\n\n{command}"

        if not messagebox.askyesno("Run Command", confirm_text):
            return

        if self.admin_var.get():
            display_command = f"pkexec sh -c {shlex.quote(command)}"
            args = ["pkexec", "sh", "-c", command]
        else:
            display_command = command
            args = ["sh", "-c", command]

        self.write_output(f"$ {display_command}\n")

        try:
            process = subprocess.run(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            if process.stdout:
                self.write_output(process.stdout)

            self.write_output(
                f"\n[Exit code: {process.returncode}]\n"
                + "-" * 75 + "\n"
            )

        except FileNotFoundError as e:
            if self.admin_var.get():
                self.write_output(
                    "\nERROR: pkexec was not found.\n"
                    "Install PolicyKit / pkexec or turn off administrator mode.\n"
                )
            else:
                self.write_output(f"\nERROR: {e}\n")

        except Exception as e:
            self.write_output(f"\nERROR: {e}\n")

    # ---------------------------------------------------------
    # Output helper
    # ---------------------------------------------------------
    def write_output(self, text):
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def clear_output(self):
        self.output_text.delete("1.0", "end")


def main():
    root = tk.Tk()
    LinuxCommandFrontend(root)
    root.mainloop()


if __name__ == "__main__":
    main()
