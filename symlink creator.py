import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os

class CommandGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Command Launcher")

        # Source
        tk.Label(root, text="Source").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )

        self.source_var = tk.StringVar()

        tk.Entry(
            root,
            textvariable=self.source_var,
            width=60
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            root,
            text="Browse",
            command=self.select_source
        ).grid(row=0, column=2, padx=5, pady=5)

        # Destination
        tk.Label(root, text="Destination").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )

        self.dest_var = tk.StringVar()

        tk.Entry(
            root,
            textvariable=self.dest_var,
            width=60
        ).grid(row=1, column=1, padx=5, pady=5)

        tk.Button(
            root,
            text="Browse",
            command=self.select_destination
        ).grid(row=1, column=2, padx=5, pady=5)

        # Buttons
        tk.Button(
            root,
            text="Create Symlink",
            command=self.create_symlink
        ).grid(row=2, column=0, pady=10)

        tk.Button(
            root,
            text="Show Command",
            command=self.show_command
        ).grid(row=2, column=1, pady=10)

        # Status
        self.status = tk.Label(root, text="", anchor="w")
        self.status.grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=5
        )

    def select_source(self):
        path = filedialog.askopenfilename()

        if path:
            self.source_var.set(path)

    def select_destination(self):
        path = filedialog.asksaveasfilename()

        if path:
            self.dest_var.set(path)

    def create_symlink(self):

        source = self.source_var.get()
        dest = self.dest_var.get()

        if not source or not dest:
            messagebox.showerror(
                "Error",
                "Select source and destination first."
            )
            return

        try:
            os.symlink(source, dest)

            self.status.config(
                text=f"Symlink created:\n{dest}"
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_command(self):

        source = self.source_var.get()
        dest = self.dest_var.get()

        cmd = f'ln -s "{source}" "{dest}"'

        messagebox.showinfo(
            "Command",
            cmd
        )

root = tk.Tk()
app = CommandGUI(root)
root.mainloop()
