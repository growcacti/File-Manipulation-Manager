#!/usr/bin/env python3
"""Advanced recursive file/folder renamer - standard library only."""

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


METHODS = {
    "Add": [("text", "Text", "str", ""), ("where", "Location", "choice", ["Beginning", "End", "Position"]), ("position", "Position (1 = first)", "int", 1), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "Replace": [("find", "Find", "str", ""), ("replace", "Replace with", "str", ""), ("regex", "Use regular expression", "bool", False), ("case", "Case sensitive", "bool", False), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "Remove": [("mode", "Remove by", "choice", ["Position", "Pattern", "Character list", "Numbers", "Non-word characters"]), ("position", "Starting position", "int", 1), ("count", "Character count", "int", 1), ("pattern", "Pattern / characters", "str", ""), ("regex", "Pattern is regular expression", "bool", False), ("backwards", "Count position from end", "bool", False), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "Move": [("source", "Move from position", "int", 1), ("count", "Character count", "int", 1), ("destination", "Move to position", "int", 1), ("backwards", "Count source from end", "bool", False), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "New Case": [("style", "New case", "choice", ["lower", "UPPER", "Title Case", "Sentence case", "Invert"]), ("location", "Location", "choice", ["All", "First letter", "First letter of every word", "Pattern", "Position"]), ("pattern", "Pattern", "str", ""), ("position", "Position", "int", 1), ("count", "Position character count", "int", 1), ("regex", "Pattern is regular expression", "bool", False), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "New Name": [("template", "Template", "str", "{name}_{num}"), ("padding", "Number padding", "int", 3), ("start", "Number start", "int", 1), ("step", "Number step", "int", 1), ("keep_ext", "Keep current extension", "bool", True)],
    "Renumber": [("which", "Which number in name", "int", 1), ("mode", "Mode", "choice", ["Absolute", "Relative"]), ("value", "New start / amount", "int", 1), ("step", "Step", "int", 1), ("padding", "Zero padding (0 = keep)", "int", 0)],
    "Swap": [("first", "First text", "str", ""), ("second", "Second text", "str", ""), ("case", "Case sensitive", "bool", False), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "Trim": [("mode", "Trim", "choice", ["Outer spaces", "Repeated spaces", "Outer separators", "All"]), ("separators", "Separators", "str", " _-."), ("apply", "Apply to", "choice", ["Name", "Extension", "Both"])],
    "Extension": [("new", "New extension (blank removes)", "str", "txt")],
}


def split_filename(filename, is_dir=False):
    if is_dir:
        return filename, ""
    p = Path(filename)
    return p.stem, p.suffix[1:]


def join_filename(name, ext, is_dir=False):
    return name if is_dir or not ext else name + "." + ext.lstrip(".")


def case_text(text, style):
    if style == "lower": return text.lower()
    if style == "UPPER": return text.upper()
    if style == "Title Case": return text.title()
    if style == "Sentence case": return text[:1].upper() + text[1:].lower()
    if style == "Invert": return text.swapcase()
    return text


def transform_part(text, rule, index, path):
    kind, p = rule["type"], rule["params"]
    if kind == "Add":
        value = p["text"]
        if p["where"] == "Beginning": return value + text
        if p["where"] == "End": return text + value
        at = max(0, min(len(text), int(p["position"]) - 1))
        return text[:at] + value + text[at:]
    if kind == "Replace":
        if not p["find"]: return text
        if p["regex"]:
            return re.sub(p["find"], p["replace"], text, flags=0 if p["case"] else re.I)
        if p["case"]: return text.replace(p["find"], p["replace"])
        return re.sub(re.escape(p["find"]), lambda _m: p["replace"], text, flags=re.I)
    if kind == "Remove":
        mode = p["mode"]
        if mode == "Position":
            pos, count = max(1, int(p["position"])), max(0, int(p["count"]))
            start = max(0, len(text) - pos) if p["backwards"] else min(len(text), pos - 1)
            return text[:start] + text[start + count:]
        if mode == "Numbers": return re.sub(r"\d", "", text)
        if mode == "Non-word characters": return re.sub(r"[^\w]", "", text)
        if mode == "Character list": return text.translate(str.maketrans("", "", p["pattern"]))
        if not p["pattern"]: return text
        pattern = p["pattern"] if p["regex"] else re.escape(p["pattern"]).replace(r"\*", ".*")
        return re.sub(pattern, "", text)
    if kind == "Move":
        pos, count = max(1, int(p["source"])), max(0, int(p["count"]))
        start = max(0, len(text) - pos) if p["backwards"] else min(len(text), pos - 1)
        chunk, rest = text[start:start + count], text[:start] + text[start + count:]
        dest = max(0, min(len(rest), int(p["destination"]) - 1))
        return rest[:dest] + chunk + rest[dest:]
    if kind == "New Case":
        style, loc = p["style"], p["location"]
        if loc == "All": return case_text(text, style)
        if loc == "First letter": return case_text(text[:1], style) + text[1:]
        if loc == "First letter of every word": return re.sub(r"\b\w", lambda m: case_text(m.group(), style), text)
        if loc == "Position":
            start, count = max(0, int(p["position"]) - 1), max(1, int(p["count"]))
            return text[:start] + case_text(text[start:start + count], style) + text[start + count:]
        if not p["pattern"]: return text
        pattern = p["pattern"] if p["regex"] else re.escape(p["pattern"])
        return re.sub(pattern, lambda m: case_text(m.group(), style), text)
    if kind == "Swap":
        a, b = p["first"], p["second"]
        if not a or not b: return text
        flags = 0 if p["case"] else re.I
        marker = "__SWAP_" + uuid.uuid4().hex + "__"
        text = re.sub(re.escape(a), marker, text, flags=flags)
        text = re.sub(re.escape(b), a, text, flags=flags)
        return text.replace(marker, b)
    if kind == "Trim":
        if p["mode"] in ("Outer spaces", "All"): text = text.strip()
        if p["mode"] in ("Repeated spaces", "All"): text = re.sub(r"\s+", " ", text)
        if p["mode"] in ("Outer separators", "All"): text = text.strip(p["separators"])
        return text
    return text


def apply_rule(filename, rule, index, path, is_dir=False):
    name, ext = split_filename(filename, is_dir)
    kind, p = rule["type"], rule["params"]
    if kind == "New Name":
        stat = path.stat()
        dt = datetime.fromtimestamp(stat.st_mtime)
        number = p["start"] + index * p["step"]
        values = {"name": name, "ext": ext, "parent": path.parent.name,
                  "date": dt.strftime("%Y-%m-%d"), "time": dt.strftime("%H-%M-%S"),
                  "size": stat.st_size, "num": str(number).zfill(max(1, p["padding"]))}
        try: new = p["template"].format_map(values)
        except KeyError as exc: raise ValueError(f"Unknown template tag: {exc}")
        return join_filename(new, ext if p["keep_ext"] else "", is_dir)
    if kind == "Renumber":
        matches = list(re.finditer(r"\d+", name))
        which = p["which"] - 1
        if 0 <= which < len(matches):
            m = matches[which]
            value = p["value"] + index * p["step"] if p["mode"] == "Absolute" else int(m.group()) + p["value"]
            width = p["padding"] or len(m.group())
            name = name[:m.start()] + str(value).zfill(width) + name[m.end():]
        return join_filename(name, ext, is_dir)
    if kind == "Extension": return join_filename(name, p["new"].lstrip("."), is_dir)
    apply_to = p.get("apply", "Name")
    if apply_to in ("Name", "Both"): name = transform_part(name, rule, index, path)
    if apply_to in ("Extension", "Both") and not is_dir: ext = transform_part(ext, rule, index, path)
    return join_filename(name, ext, is_dir)


class RuleDialog(simpledialog.Dialog):
    def __init__(self, parent, method, values=None):
        self.method, self.values, self.vars = method, values or {}, {}
        super().__init__(parent, title=method + " method")

    def body(self, frame):
        for row, (key, label, typ, default) in enumerate(METHODS[self.method]):
            ttk.Label(frame, text=label + ":").grid(row=row, column=0, sticky="w", padx=5, pady=4)
            value = self.values.get(key, default[0] if typ == "choice" else default)
            if typ == "bool":
                var = tk.BooleanVar(value=value); widget = ttk.Checkbutton(frame, variable=var)
            elif typ == "int":
                var = tk.IntVar(value=value); widget = ttk.Spinbox(frame, from_=-999999, to=999999, textvariable=var, width=18)
            elif typ == "choice":
                var = tk.StringVar(value=value); widget = ttk.Combobox(frame, textvariable=var, values=default, state="readonly", width=25)
            else:
                var = tk.StringVar(value=value); widget = ttk.Entry(frame, textvariable=var, width=32)
            self.vars[key] = var; widget.grid(row=row, column=1, sticky="ew", padx=5, pady=4)
        return next(iter(frame.winfo_children()), None)

    def validate(self):
        try: [v.get() for v in self.vars.values()]; return True
        except tk.TclError: messagebox.showerror("Invalid value", "Please check the number fields.", parent=self); return False

    def apply(self): self.result = {k: v.get() for k, v in self.vars.items()}


class AdvancedRenamer(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Advanced Recursive Batch Renamer"); self.geometry("1280x800"); self.minsize(980, 650)
        self.folder = tk.StringVar(); self.extensions = tk.StringVar(value="*"); self.include_files = tk.BooleanVar(value=True); self.include_dirs = tk.BooleanVar(value=False); self.include_hidden = tk.BooleanVar(value=False)
        self.method = tk.StringVar(value="Replace"); self.status = tk.StringVar(value="Choose a folder, add methods, and review the preview.")
        self.items, self.rules, self.last_rename = [], [], []
        self.build()

    def build(self):
        self.columnconfigure(0, weight=1); self.rowconfigure(2, weight=1)
        top = ttk.Frame(self, padding=10); top.grid(sticky="ew"); top.columnconfigure(1, weight=1)
        ttk.Label(top, text="Advanced Recursive Batch Renamer", font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0,8))
        ttk.Label(top, text="Root folder:").grid(row=1,column=0); ttk.Entry(top,textvariable=self.folder).grid(row=1,column=1,sticky="ew",padx=5)
        ttk.Button(top,text="Choose...",command=self.choose).grid(row=1,column=2); ttk.Button(top,text="Scan",command=self.scan).grid(row=1,column=3,padx=5)
        ttk.Label(top,text="Extensions:").grid(row=2,column=0); ttk.Entry(top,textvariable=self.extensions,width=20).grid(row=2,column=1,sticky="w",padx=5)
        ttk.Label(top,text="Examples:  *   .log   .jpg,.png,.txt").grid(row=3,column=1,sticky="w",padx=5)
        ttk.Checkbutton(top,text="Files",variable=self.include_files,command=self.scan).grid(row=2,column=2); ttk.Checkbutton(top,text="Folders",variable=self.include_dirs,command=self.scan).grid(row=2,column=3)
        ttk.Checkbutton(top,text="Include hidden",variable=self.include_hidden,command=self.scan).grid(row=2,column=4,padx=(5,0))
        rules = ttk.LabelFrame(self,text="Rename methods — applied from top to bottom",padding=8); rules.grid(row=1,column=0,sticky="ew",padx=10); rules.columnconfigure(1,weight=1)
        ttk.Combobox(rules,textvariable=self.method,values=list(METHODS),state="readonly",width=18).grid(row=0,column=0,padx=(0,5)); ttk.Button(rules,text="Add Method",command=self.add_rule).grid(row=0,column=1,sticky="w")
        self.rule_list = tk.Listbox(rules,height=6,exportselection=False); self.rule_list.grid(row=1,column=0,columnspan=2,sticky="ew",pady=6); self.rule_list.bind("<Double-1>",lambda _e:self.edit_rule())
        buttons=ttk.Frame(rules); buttons.grid(row=1,column=2,sticky="ns",padx=5)
        for text_,cmd in [("Edit",self.edit_rule),("Up",lambda:self.move_rule(-1)),("Down",lambda:self.move_rule(1)),("Duplicate",self.duplicate_rule),("Remove",self.remove_rule)]: ttk.Button(buttons,text=text_,command=cmd,width=10).pack(fill="x",pady=1)
        profile=ttk.Frame(rules); profile.grid(row=0,column=2,sticky="e"); ttk.Button(profile,text="Save Rules...",command=self.save_rules).pack(side="left",padx=2); ttk.Button(profile,text="Load Rules...",command=self.load_rules).pack(side="left",padx=2); ttk.Button(profile,text="Clear",command=self.clear_rules).pack(side="left",padx=2)
        frame=ttk.Frame(self); frame.grid(row=2,column=0,sticky="nsew",padx=10,pady=8); frame.columnconfigure(0,weight=1); frame.rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(frame,columns=("type","old","new","folder","status"),show="headings")
        for c,t,w in [("type","Type",65),("old","Current Name",230),("new","New Name",260),("folder","Folder",360),("status","Status",90)]: self.tree.heading(c,text=t); self.tree.column(c,width=w)
        y=ttk.Scrollbar(frame,orient="vertical",command=self.tree.yview); x=ttk.Scrollbar(frame,orient="horizontal",command=self.tree.xview); self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set); self.tree.grid(sticky="nsew"); y.grid(row=0,column=1,sticky="ns"); x.grid(row=1,column=0,sticky="ew")
        bottom=ttk.Frame(self,padding=10); bottom.grid(row=3,column=0,sticky="ew"); bottom.columnconfigure(0,weight=1); ttk.Label(bottom,textvariable=self.status).grid(row=0,column=0,sticky="w"); ttk.Button(bottom,text="Undo Last Batch",command=self.undo).grid(row=0,column=1,padx=5); ttk.Button(bottom,text="RENAME",command=self.rename).grid(row=0,column=2)

    def choose(self):
        value=filedialog.askdirectory(title="Choose root folder")
        if value: self.folder.set(value); self.scan()

    def scan(self):
        text = self.folder.get().strip()
        if not text:
            messagebox.showinfo("Choose a folder", "Choose a root folder first.")
            return
        root = Path(text).expanduser()
        if not root.is_dir():
            messagebox.showerror("Folder not found", f"This folder could not be opened:\n\n{root}")
            return
        if not self.include_files.get() and not self.include_dirs.get():
            messagebox.showinfo("Nothing selected", "Select Files, Folders, or both.")
            self.items = []; self.preview(); return

        extension_text = self.extensions.get().strip()
        allowed = set()
        for item in extension_text.split(","):
            item = item.strip().lower()
            if not item:
                continue
            if item.startswith("*."):
                item = item[2:]
            else:
                item = item.lstrip(".")
            allowed.add(item)
        all_extensions = not allowed or "*" in allowed
        found, errors = [], []

        def walk_error(error):
            errors.append(str(error))

        # os.walk is used here because it lets us safely skip inaccessible
        # folders and prune hidden folders before entering them.
        for current, directory_names, file_names in os.walk(root, topdown=True, onerror=walk_error, followlinks=False):
            current_path = Path(current)
            if not self.include_hidden.get():
                directory_names[:] = [d for d in directory_names if not d.startswith(".")]
                file_names = [f for f in file_names if not f.startswith(".")]

            if self.include_dirs.get():
                for directory_name in directory_names:
                    found.append((current_path / directory_name, True))

            if self.include_files.get():
                for file_name in file_names:
                    path = current_path / file_name
                    extension = path.suffix.lower().lstrip(".")
                    if all_extensions or extension in allowed:
                        found.append((path, False))

        self.items = sorted(found, key=lambda item: str(item[0]).casefold())
        self.scan_errors = errors
        self.preview()

    def describe(self,r):
        p=r["params"]; return r["type"]+" — "+", ".join(f"{k}={v}" for k,v in list(p.items())[:3])

    def redraw_rules(self):
        self.rule_list.delete(0,"end")
        for r in self.rules: self.rule_list.insert("end",self.describe(r))
        self.preview()

    def add_rule(self):
        d=RuleDialog(self,self.method.get())
        if d.result is not None: self.rules.append({"type":self.method.get(),"params":d.result}); self.redraw_rules()

    def selected(self):
        s=self.rule_list.curselection(); return s[0] if s else None

    def edit_rule(self):
        i=self.selected()
        if i is None:return
        r=self.rules[i]; d=RuleDialog(self,r["type"],r["params"])
        if d.result is not None:r["params"]=d.result;self.redraw_rules();self.rule_list.selection_set(i)

    def move_rule(self,direction):
        i=self.selected()
        if i is None:return
        j=i+direction
        if 0<=j<len(self.rules):self.rules[i],self.rules[j]=self.rules[j],self.rules[i];self.redraw_rules();self.rule_list.selection_set(j)

    def duplicate_rule(self):
        i=self.selected()
        if i is not None:self.rules.insert(i+1,json.loads(json.dumps(self.rules[i])));self.redraw_rules();self.rule_list.selection_set(i+1)

    def remove_rule(self):
        i=self.selected()
        if i is not None:self.rules.pop(i);self.redraw_rules()

    def clear_rules(self):
        if not self.rules or messagebox.askyesno("Clear rules","Remove all rename methods?"):self.rules.clear();self.redraw_rules()

    def save_rules(self):
        path=filedialog.asksaveasfilename(title="Save rename rules",defaultextension=".json",filetypes=[("Rename rules","*.json")])
        if path:
            try:
                with open(path,"w",encoding="utf-8") as f:json.dump({"version":1,"rules":self.rules},f,indent=2)
            except OSError as e:messagebox.showerror("Save failed",str(e))

    def load_rules(self):
        path=filedialog.askopenfilename(title="Load rename rules",filetypes=[("Rename rules","*.json"),("All files","*")])
        if path:
            try:
                with open(path,encoding="utf-8") as f:data=json.load(f)
                rules=data["rules"]
                if not isinstance(rules,list) or any(r.get("type") not in METHODS for r in rules):raise ValueError("Not a valid rules file")
                self.rules=rules;self.redraw_rules()
            except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:messagebox.showerror("Load failed",str(e))

    def proposed(self):
        rows=[]
        for index,(path,is_dir) in enumerate(self.items):
            new=path.name
            try:
                for rule in self.rules:new=apply_rule(new,rule,index,path,is_dir)
                status="UNCHANGED" if new==path.name else "READY"
                if not new or new in (".","..") or any(c in new for c in '/\0'):status="INVALID"
            except (ValueError,re.error,OSError) as e:new=str(e);status="ERROR"
            rows.append((path,is_dir,new,status))
        counts={}
        for p,_d,n,s in rows:
            if s=="READY":counts[os.path.normcase(str(p.with_name(n)))]=counts.get(os.path.normcase(str(p.with_name(n))),0)+1
        out=[]
        for p,d,n,s in rows:
            dest=p.with_name(n);key=os.path.normcase(str(dest))
            if s=="READY" and counts[key]>1:s="DUPLICATE"
            elif s=="READY" and dest.exists():s="EXISTS"
            out.append((p,d,n,s))
        return out

    def preview(self):
        if not hasattr(self,"tree"):return
        self.tree.delete(*self.tree.get_children());ready=0
        for p,d,n,s in self.proposed():
            if s=="READY":ready+=1
            self.tree.insert("","end",values=("Folder" if d else "File",p.name,n,str(p.parent),s))
        error_note = f" — {len(getattr(self, 'scan_errors', []))} inaccessible folder(s) skipped" if getattr(self, "scan_errors", []) else ""
        self.status.set(f"{len(self.items)} item(s) found, {len(self.rules)} method(s), {ready} ready{error_note}.")

    def rename(self):
        rows=self.proposed();bad=[r for r in rows if r[3] not in ("READY","UNCHANGED")];plan=[(p,p.with_name(n),d) for p,d,n,s in rows if s=="READY"]
        if bad:messagebox.showerror("Cannot rename","Resolve items marked INVALID, ERROR, EXISTS, or DUPLICATE first.");return
        if not plan:messagebox.showinfo("Nothing to rename","The current methods do not change any names.");return
        if not messagebox.askyesno("Confirm",f"Rename {len(plan)} item(s)?\n\nReview the preview first. Existing items will not be overwritten."):return
        completed=[]
        try:
            files=[x for x in plan if not x[2]];dirs=sorted([x for x in plan if x[2]],key=lambda x:len(x[0].parts),reverse=True)
            for source,dest,_ in files+dirs:
                if not source.exists():continue
                source.rename(dest);completed.append((dest,source))
        except OSError as e:
            for current,original in reversed(completed):
                try:
                    if current.exists() and not original.exists():current.rename(original)
                except OSError:pass
            messagebox.showerror("Rename failed",f"{e}\n\nA rollback was attempted.");self.scan();return
        self.last_rename=completed;messagebox.showinfo("Complete",f"Renamed {len(completed)} item(s).");self.scan()

    def undo(self):
        if not self.last_rename:messagebox.showinfo("Undo","There is no batch to undo.");return
        restored=0
        for current,original in reversed(self.last_rename):
            try:
                if current.exists() and not original.exists():current.rename(original);restored+=1
            except OSError:pass
        self.last_rename=[];self.scan();messagebox.showinfo("Undo",f"Restored {restored} item(s).")


if __name__ == "__main__":
    AdvancedRenamer().mainloop()
