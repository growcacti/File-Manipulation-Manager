#!/usr/bin/env python3
import os
import shlex
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class MultiDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MultiDownloader GUI")
        self.root.geometry("900x650")
        self.root.minsize(760, 560)

        # Variables
        self.tool_var = tk.StringVar(value="wget")
        self.url_var = tk.StringVar()
        self.filename_var = tk.StringVar()
        self.verbose_var = tk.BooleanVar(value=False)

        self.depth_var = tk.StringVar(value="3")
        self.ext_depth_var = tk.StringVar(value="0")
        self.connections_var = tk.StringVar(value="4")

        self.process = None

        self.build_gui()
        self.update_tool_fields()

    def build_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # ---------------- Top settings frame ----------------
        settings = ttk.LabelFrame(self.root, text="Download Settings", padding=10)
        settings.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Tool:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )

        tool_frame = ttk.Frame(settings)
        tool_frame.grid(row=0, column=1, columnspan=2, sticky="w")

        ttk.Radiobutton(
            tool_frame,
            text="wget",
            variable=self.tool_var,
            value="wget",
            command=self.update_tool_fields
        ).grid(row=0, column=0, padx=5)

        ttk.Radiobutton(
            tool_frame,
            text="curl",
            variable=self.tool_var,
            value="curl",
            command=self.update_tool_fields
        ).grid(row=0, column=1, padx=5)

        ttk.Radiobutton(
            tool_frame,
            text="HTTrack",
            variable=self.tool_var,
            value="httrack",
            command=self.update_tool_fields
        ).grid(row=0, column=2, padx=5)

        ttk.Label(settings, text="URL:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(settings, textvariable=self.url_var).grid(
            row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew"
        )

        self.destination_label = ttk.Label(settings, text="Output file:")
        self.destination_label.grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )

        ttk.Entry(settings, textvariable=self.filename_var).grid(
            row=2, column=1, padx=5, pady=5, sticky="ew"
        )

        self.browse_button = ttk.Button(
            settings, text="Browse...", command=self.browse_destination
        )
        self.browse_button.grid(
            row=2, column=2, padx=5, pady=5, sticky="ew"
        )

        self.verbose_check = ttk.Checkbutton(
            settings, text="Verbose output", variable=self.verbose_var
        )
        self.verbose_check.grid(
            row=3, column=1, padx=5, pady=5, sticky="w"
        )

        # ---------------- HTTrack options ----------------
        self.httrack_frame = ttk.LabelFrame(
            settings, text="HTTrack Mirror Options", padding=8
        )
        self.httrack_frame.grid(
            row=4, column=0, columnspan=3, padx=5, pady=8, sticky="ew"
        )

        self.httrack_frame.columnconfigure(1, weight=1)
        self.httrack_frame.columnconfigure(3, weight=1)
        self.httrack_frame.columnconfigure(5, weight=1)

        ttk.Label(self.httrack_frame, text="Depth:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            self.httrack_frame, textvariable=self.depth_var, width=8
        ).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.httrack_frame, text="External depth:").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            self.httrack_frame, textvariable=self.ext_depth_var, width=8
        ).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(self.httrack_frame, text="Connections:").grid(
            row=0, column=4, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            self.httrack_frame, textvariable=self.connections_var, width=8
        ).grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # ---------------- Buttons ----------------
        button_frame = ttk.Frame(settings)
        button_frame.grid(
            row=5, column=0, columnspan=3, pady=(5, 0), sticky="ew"
        )

        for col in range(5):
            button_frame.columnconfigure(col, weight=1)

        self.start_button = ttk.Button(
            button_frame, text="Start Download", command=self.start_download
        )
        self.start_button.grid(row=0, column=0, padx=4, sticky="ew")

        self.stop_button = ttk.Button(
            button_frame, text="Stop", command=self.stop_download,
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=4, sticky="ew")

        ttk.Button(
            button_frame, text="Clear Output", command=self.clear_output
        ).grid(row=0, column=2, padx=4, sticky="ew")

        ttk.Button(
            button_frame, text="Check Tools", command=self.check_tools
        ).grid(row=0, column=3, padx=4, sticky="ew")

        ttk.Button(
            button_frame, text="Exit", command=self.root.destroy
        ).grid(row=0, column=4, padx=4, sticky="ew")

        # ---------------- Output frame ----------------
        output_frame = ttk.LabelFrame(
            self.root, text="Command Output", padding=8
        )
        output_frame.grid(
            row=1, column=0, padx=10, pady=(0, 10), sticky="nsew"
        )

        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(
            output_frame,
            wrap="word",
            font=("Monospace", 10)
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            output_frame,
            orient="vertical",
            command=self.output_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar.set)

        # ---------------- Status bar ----------------
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w"
        )
        status.grid(row=2, column=0, sticky="ew")

    def update_tool_fields(self):
        tool = self.tool_var.get()

        if tool == "httrack":
            self.destination_label.configure(text="Mirror folder:")
            self.set_httrack_state("normal")
        else:
            self.destination_label.configure(text="Output file:")
            self.set_httrack_state("disabled")

    def set_httrack_state(self, state):
        for child in self.httrack_frame.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

    def browse_destination(self):
        if self.tool_var.get() == "httrack":
            selected = filedialog.askdirectory(
                title="Select mirror output folder"
            )
        else:
            selected = filedialog.asksaveasfilename(
                title="Choose output filename"
            )

        if selected:
            self.filename_var.set(selected)

    def append_output(self, text):
        self.output_text.insert("end", text)
        self.output_text.see("end")

    def thread_safe_output(self, text):
        self.root.after(0, self.append_output, text)

    def clear_output(self):
        self.output_text.delete("1.0", "end")

    def check_tools(self):
        self.append_output("\nInstalled tools:\n")
        for tool in ("curl", "wget", "httrack"):
            location = shutil.which(tool)
            if location:
                self.append_output(f"  {tool}: {location}\n")
            else:
                self.append_output(f"  {tool}: NOT FOUND\n")
        self.append_output("\n")

    def validate(self):
        url = self.url_var.get().strip()
        destination = self.filename_var.get().strip()

        if not url:
            messagebox.showwarning("Missing URL", "Please enter a URL.")
            return False

        if not destination:
            messagebox.showwarning(
                "Missing destination",
                "Please choose an output file or folder."
            )
            return False

        tool = self.tool_var.get()

        if shutil.which(tool) is None:
            messagebox.showerror(
                "Program not found",
                f"{tool} is not installed or is not in PATH."
            )
            return False

        if tool == "httrack":
            for label, value in (
                ("Depth", self.depth_var.get()),
                ("External depth", self.ext_depth_var.get()),
                ("Connections", self.connections_var.get())
            ):
                try:
                    int(value)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid value",
                        f"{label} must be a whole number."
                    )
                    return False

        return True

    def build_command(self):
        tool = self.tool_var.get()
        url = self.url_var.get().strip()
        destination = self.filename_var.get().strip()

        if tool == "wget":
            command = ["wget"]

            if self.verbose_var.get():
                command.append("-v")

            command.extend(["-O", destination, url])
            return command

        if tool == "curl":
            command = ["curl", "-L"]

            if self.verbose_var.get():
                command.append("-v")

            # -o correctly saves to the filename chosen by the user.
            command.extend(["-o", destination, url])
            return command

        if tool == "httrack":
            command = [
                "httrack",
                url,
                "-O", destination,
                f"-r{self.depth_var.get().strip()}",
                f"-%e{self.ext_depth_var.get().strip()}",
                f"-c{self.connections_var.get().strip()}"
            ]

            if self.verbose_var.get():
                command.append("-v")

            return command

        raise ValueError("Unknown download tool.")

    def start_download(self):
        if not self.validate():
            return

        command = self.build_command()

        self.append_output("\n----------------------------------------\n")
        self.append_output("Running:\n")
        self.append_output(" ".join(shlex.quote(part) for part in command) + "\n\n")

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set("Running...")

        thread = threading.Thread(
            target=self.run_command,
            args=(command,),
            daemon=True
        )
        thread.start()

    def run_command(self, command):
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            if self.process.stdout:
                for line in self.process.stdout:
                    self.thread_safe_output(line)

            return_code = self.process.wait()

            if return_code == 0:
                self.thread_safe_output("\nCompleted successfully.\n")
                self.root.after(
                    0, lambda: self.status_var.set("Completed")
                )
            else:
                self.thread_safe_output(
                    f"\nCommand ended with code {return_code}.\n"
                )
                self.root.after(
                    0,
                    lambda: self.status_var.set(
                        f"Stopped / error ({return_code})"
                    )
                )

        except Exception as exc:
            self.thread_safe_output(f"\nERROR: {exc}\n")
            self.root.after(
                0, lambda: self.status_var.set("Error")
            )

        finally:
            self.process = None
            self.root.after(
                0,
                lambda: self.start_button.configure(state="normal")
            )
            self.root.after(
                0,
                lambda: self.stop_button.configure(state="disabled")
            )

    def stop_download(self):
        if self.process and self.process.poll() is None:
            self.append_output("\nStopping command...\n")
            try:
                self.process.terminate()
            except Exception as exc:
                self.append_output(f"Could not stop process: {exc}\n")

    def on_close(self):
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno(
                "Download running",
                "A download is still running. Exit anyway?"
            ):
                return

            try:
                self.process.terminate()
            except Exception:
                pass

        self.root.destroy()


def main():
    root = tk.Tk()
    app = MultiDownloaderGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

