
import json
import os
import csv
import customtkinter as ctk
from tkinter import messagebox, Toplevel, filedialog
from tkcalendar import Calendar
from datetime import datetime, date
from pathlib import Path

# Optional pandas for Excel export/import
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False

# --- Constants ---
TASK_FILE = "tasks.json"

# --- File I/O ---
def save_tasks(tasks):
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

def load_tasks():
    if not os.path.exists(TASK_FILE):
        return []
    with open(TASK_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_task_id(tasks):
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1

# --- Calendar Popup (improved) ---
class CalendarPopup(Toplevel):
    def __init__(self, parent, callback, current_date=None):
        super().__init__(parent)
        self.title("📅 Select Date")
        self.geometry("520x460")
        self.resizable(False, False)
        self.callback = callback
        self.grab_set()
        self.focus_force()

        dt = current_date if current_date else datetime.today()

        self.cal = Calendar(
            self,
            selectmode='day',
            year=dt.year,
            month=dt.month,
            day=dt.day,
            font=("Helvetica", 13),
            background="white",
            foreground="black",
            headersbackground="#d9e6f2",
            headersforeground="black",
            selectbackground="#2f74c0",
            selectforeground="white",
            weekendbackground="#fff2e6",
            weekendforeground="black",
            othermonthforeground="#9aa8b2",
            showweeknumbers=True,
            firstweekday="sunday"
        )
        self.cal.pack(padx=12, pady=12, fill="both", expand=True)

        # Mark today
        try:
            today = datetime.today().date()
            self.cal.calevent_remove('all')
            self.cal.calevent_create(today, 'Today', 'today')
            self.cal.tag_config('today', background='#ffef8a', foreground='black')
        except Exception:
            pass

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=8)
        ctk.CTkButton(btn_frame, text="✅ Select", width=120, command=self.select_date).grid(row=0, column=0, padx=12)
        ctk.CTkButton(btn_frame, text="❌ Cancel", width=120, fg_color="red", command=self.destroy).grid(row=0, column=1, padx=12)

    def select_date(self):
        try:
            d = self.cal.selection_get()
            if not d:
                d = datetime.today().date()
        except Exception:
            try:
                ds = self.cal.get_date()
                d = datetime.strptime(ds, "%m/%d/%y").date()
            except Exception:
                d = datetime.today().date()
        self.callback(d.strftime("%Y-%m-%d"))
        self.destroy()

# --- Custom dialogs (Update/Delete/Toggle) ---
class UpdateTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent, task, save_callback):
        super().__init__(parent)
        self.title("✏️ Update Task")
        self.geometry("560x380")
        self.task = task
        self.save_callback = save_callback
        self.grab_set()
        self.focus_force()

        ctk.CTkLabel(self, text=f"Update Task ID {task['id']}", font=("Arial", 20, "bold")).pack(pady=12)

        ctk.CTkLabel(self, text="Task:", font=("Arial", 14)).pack(anchor="w", padx=16)
        self.task_entry = ctk.CTkEntry(self, width=500)
        self.task_entry.insert(0, task["task"])
        self.task_entry.pack(padx=16, pady=6)

        ctk.CTkLabel(self, text="Due Date:", font=("Arial", 14)).pack(anchor="w", padx=16, pady=(6,0))
        self.due_date_var = ctk.StringVar()
        if task.get("due_date") and task["due_date"] != "No due date":
            self.due_date_var.set(task["due_date"])
        else:
            self.due_date_var.set(datetime.today().strftime("%Y-%m-%d"))
        self.due_date_entry = ctk.CTkEntry(self, width=220, textvariable=self.due_date_var, state="readonly")
        self.due_date_entry.pack(padx=16, pady=6)
        self.due_date_entry.bind("<1>", self.open_calendar)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=16)
        ctk.CTkButton(btn_frame, text="💾 Save", width=140, command=self.save).grid(row=0, column=0, padx=12)
        ctk.CTkButton(btn_frame, text="❌ Cancel", width=140, fg_color="red", command=self.destroy).grid(row=0, column=1, padx=12)

    def open_calendar(self, event):
        def cb(date_str):
            self.due_date_var.set(date_str)
        try:
            cur = datetime.strptime(self.due_date_var.get(), "%Y-%m-%d")
        except Exception:
            cur = datetime.today()
        CalendarPopup(self, cb, cur)

    def save(self):
        new_text = self.task_entry.get().strip()
        new_due = self.due_date_var.get().strip()
        if not new_text:
            messagebox.showwarning("Invalid Input", "Task cannot be empty.")
            return
        try:
            datetime.strptime(new_due, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Invalid Date", "Please select a valid date.")
            return
        self.task["task"] = new_text
        self.task["due_date"] = new_due
        self.save_callback(self.task)
        self.destroy()

class DeleteTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent, task, delete_callback):
        super().__init__(parent)
        self.title("❌ Delete Task")
        self.geometry("420x220")
        self.task = task
        self.delete_callback = delete_callback
        self.grab_set()
        self.focus_force()

        ctk.CTkLabel(self, text=f"Are you sure you want to delete?\n\n{task['task']}", font=("Arial", 16), wraplength=380).pack(pady=18)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="✅ Yes", width=120, command=self.confirm).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="❌ No", width=120, fg_color="red", command=self.destroy).grid(row=0, column=1, padx=10)

    def confirm(self):
        self.delete_callback(self.task)
        self.destroy()

class ToggleTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent, task, toggle_callback):
        super().__init__(parent)
        self.title("🔄 Toggle Completion")
        self.geometry("420x220")
        self.task = task
        self.toggle_callback = toggle_callback
        self.grab_set()
        self.focus_force()

        status_text = "completed ✅" if not task["completed"] else "not completed ❌"
        ctk.CTkLabel(self, text=f"Mark task as {status_text}?\n\n{task['task']}", font=("Arial", 16), wraplength=380).pack(pady=18)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="✅ Yes", width=120, command=self.confirm).grid(row=0, column=0, padx=10)
        ctk.CTkButton(btn_frame, text="❌ No", width=120, fg_color="red", command=self.destroy).grid(row=0, column=1, padx=10)

    def confirm(self):
        self.toggle_callback(self.task)
        self.destroy()

# --- Main App ---
class TaskManagerApp(ctk.CTk):
    ROW_BG = {
        "overdue": "#ffdddd",
        "today": "#fff3e0",
        "completed": "#e6fff0",
        "normal": None
    }

    def __init__(self):
        super().__init__()
        self.title("🚀 Advanced Task Manager")
        self.geometry("1300x880")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State
        self.tasks = load_tasks()
        self.filter_var = ctk.StringVar(value="All")
        self.sort_var = ctk.StringVar(value="ID (Ascending)")
        self.search_var = ctk.StringVar(value="")
        # ensure no pre-selection at startup
        self.selected_task_id = None  # selected via clicking row

        # Layout using grid so footer always visible
        self.grid_rowconfigure(4, weight=1)  # task list row expands
        self.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(self, text="📋 Task Manager", font=("Arial", 36, "bold")).grid(row=0, column=0, pady=14)

        # Add form
        form_frame = ctk.CTkFrame(self, corner_radius=12)
        form_frame.grid(row=1, column=0, padx=18, pady=8, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Task:", font=("Arial", 14)).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self.task_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter task here...", width=700)
        self.task_entry.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        ctk.CTkLabel(form_frame, text="Due Date:", font=("Arial", 14)).grid(row=0, column=2, padx=8, pady=6, sticky="w")
        self.due_date_var = ctk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        self.due_date_entry = ctk.CTkEntry(form_frame, width=200, textvariable=self.due_date_var, state="readonly")
        self.due_date_entry.grid(row=0, column=3, padx=8, pady=6, sticky="w")
        self.due_date_entry.bind("<1>", self.open_add_calendar)

        self.add_button = ctk.CTkButton(form_frame, text="➕ Add Task", width=140, command=self.add_task)
        self.add_button.grid(row=0, column=4, padx=12, pady=6)

        # Options: search, filter, sort, import/export
        options_frame = ctk.CTkFrame(self, corner_radius=12)
        options_frame.grid(row=2, column=0, padx=18, pady=8, sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        # Live search
        ctk.CTkLabel(options_frame, text="Search:", font=("Arial", 14)).grid(row=0, column=0, padx=8, pady=6)
        self.search_entry = ctk.CTkEntry(options_frame, textvariable=self.search_var, placeholder_text="Type to search (live)...")
        self.search_entry.grid(row=0, column=1, padx=8, pady=6, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        # Filter
        ctk.CTkLabel(options_frame, text="Filter:", font=("Arial", 14)).grid(row=0, column=2, padx=8, pady=6)
        self.filter_menu = ctk.CTkOptionMenu(options_frame, values=["All", "Completed", "Not Completed"], variable=self.filter_var, command=lambda _: self.refresh_list())
        self.filter_menu.grid(row=0, column=3, padx=8, pady=6)

        # Sort
        ctk.CTkLabel(options_frame, text="Sort By:", font=("Arial", 14)).grid(row=0, column=4, padx=8, pady=6)
        self.sort_menu = ctk.CTkOptionMenu(options_frame,
                                           values=[
                                               "ID (Ascending)", "ID (Descending)",
                                               "Alphabetical (A-Z)", "Alphabetical (Z-A)",
                                               "Completed First", "Not Completed First",
                                               "Due Date (Sooner First)", "Due Date (Latest First)"
                                           ],
                                           variable=self.sort_var, command=lambda _: self.refresh_list())
        self.sort_menu.grid(row=0, column=5, padx=8, pady=6)

        # Import/Export buttons
        io_frame = ctk.CTkFrame(options_frame)
        io_frame.grid(row=0, column=6, padx=10, pady=6)
        ctk.CTkButton(io_frame, text="⬆️ Export CSV", width=120, command=self.export_csv).grid(row=0, column=0, padx=6)
        ctk.CTkButton(io_frame, text="⬆️ Export Excel", width=120, command=self.export_excel).grid(row=0, column=1, padx=6)
        ctk.CTkButton(io_frame, text="⬇️ Import CSV", width=120, command=self.import_csv).grid(row=0, column=2, padx=6)

        # Task list area
        list_frame = ctk.CTkFrame(self, corner_radius=12)
        list_frame.grid(row=4, column=0, padx=18, pady=(8,4), sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.task_list = ctk.CTkScrollableFrame(list_frame, width=1240, height=520)
        self.task_list.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # Footer buttons (always visible)
        footer = ctk.CTkFrame(self, corner_radius=12)
        footer.grid(row=5, column=0, padx=18, pady=12, sticky="ew")
        footer.grid_columnconfigure(4, weight=1)

        self.update_btn = ctk.CTkButton(footer, text="✏️ Update Task", width=160, command=self.update_task)
        self.update_btn.grid(row=0, column=0, padx=8)
        self.delete_btn = ctk.CTkButton(footer, text="❌ Delete Task", width=160, command=self.delete_task)
        self.delete_btn.grid(row=0, column=1, padx=8)
        self.toggle_btn = ctk.CTkButton(footer, text="✅ Toggle Completion", width=160, command=self.toggle_completion)
        self.toggle_btn.grid(row=0, column=2, padx=8)

        self.switch_var = ctk.StringVar(value="dark")
        self.mode_switch = ctk.CTkSwitch(footer, text="🌙 Toggle Light/Dark Mode", variable=self.switch_var, onvalue="light", offvalue="dark", command=self.change_mode)
        self.mode_switch.grid(row=0, column=3, padx=8)

        # Selected label to show current selected task
        self.selected_label = ctk.CTkLabel(footer, text="Selected: None", anchor="e")
        self.selected_label.grid(row=0, column=4, sticky="e", padx=8)

        # initial render and startup reminders
        self.refresh_list()
        self.startup_reminder()

    # Calendar open for add
    def open_add_calendar(self, event):
        def cb(date_str):
            self.due_date_var.set(date_str)
        try:
            cur = datetime.strptime(self.due_date_var.get(), "%Y-%m-%d")
        except Exception:
            cur = datetime.today()
        CalendarPopup(self, cb, cur)

    # parse helper
    def parse_date(self, ds):
        if not ds or ds == "No due date":
            return datetime.max
        try:
            return datetime.strptime(ds, "%Y-%m-%d")
        except Exception:
            return datetime.max

    # refresh list (live search + filter + sort) and create clickable rows
    def refresh_list(self):
        # clear
        for w in self.task_list.winfo_children():
            w.destroy()

        txt = self.search_var.get().strip().lower()
        today = date.today()
        tasks_to_show = self.tasks[:]

        # filter by search text
        if txt:
            tasks_to_show = [t for t in tasks_to_show if txt in t["task"].lower()]

        # filter by completion
        if self.filter_var.get() == "Completed":
            tasks_to_show = [t for t in tasks_to_show if t["completed"]]
        elif self.filter_var.get() == "Not Completed":
            tasks_to_show = [t for t in tasks_to_show if not t["completed"]]

        # apply sort
        sort_type = self.sort_var.get()
        if sort_type == "ID (Ascending)":
            tasks_to_show.sort(key=lambda x: x["id"])
        elif sort_type == "ID (Descending)":
            tasks_to_show.sort(key=lambda x: x["id"], reverse=True)
        elif sort_type == "Alphabetical (A-Z)":
            tasks_to_show.sort(key=lambda x: x["task"].lower())
        elif sort_type == "Alphabetical (Z-A)":
            tasks_to_show.sort(key=lambda x: x["task"].lower(), reverse=True)
        elif sort_type == "Completed First":
            tasks_to_show.sort(key=lambda x: (not x["completed"], x["id"]))
        elif sort_type == "Not Completed First":
            tasks_to_show.sort(key=lambda x: (x["completed"], x["id"]))
        elif sort_type == "Due Date (Sooner First)":
            tasks_to_show.sort(key=lambda x: self.parse_date(x.get("due_date")))
        elif sort_type == "Due Date (Latest First)":
            tasks_to_show.sort(key=lambda x: self.parse_date(x.get("due_date")), reverse=True)

        # determine default text color depending on appearance mode
        appearance = ctk.get_appearance_mode()  # "dark" or "light"
        default_text_color = "white" if appearance == "dark" else "black"

        # show rows
        for task in tasks_to_show:
            row_frame = ctk.CTkFrame(self.task_list, corner_radius=8, fg_color=None)
            row_frame.pack(fill="x", pady=6, padx=6)

            # determine background color based on status
            due = task.get("due_date", "No due date")
            row_bg = None
            try:
                if due != "No due date":
                    due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
                    if not task["completed"] and due_date_obj < today:
                        row_bg = self.ROW_BG["overdue"]
                    elif not task["completed"] and due_date_obj == today:
                        row_bg = self.ROW_BG["today"]
                if task["completed"]:
                    row_bg = self.ROW_BG["completed"]
            except Exception:
                row_bg = self.ROW_BG["normal"]

            # left: summary label
            status = "✅" if task["completed"] else "❌"
            overdue_flag = ""
            try:
                if due != "No due date":
                    dd = datetime.strptime(due, "%Y-%m-%d").date()
                    if not task["completed"] and dd < today:
                        overdue_flag = "⚠️ OVERDUE"
                    elif not task["completed"] and dd == today:
                        overdue_flag = "🔶 DUE TODAY"
            except Exception:
                pass

            label_text = f"ID {task['id']} | {task['task']} [{status}] - Due: {due} {overdue_flag}"

            # create label with default readable color
            lbl = ctk.CTkLabel(row_frame, text=label_text, anchor="w", font=("Arial", 13), wraplength=1000, text_color=default_text_color)
            lbl.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            # small action buttons on right for quick update/delete/toggle
            btn_frame = ctk.CTkFrame(row_frame, fg_color=None)
            btn_frame.pack(side="right", padx=8)

            quick_update = ctk.CTkButton(btn_frame, text="✏️", width=48, height=36, command=lambda t=task: self.open_update_dialog(t))
            quick_update.grid(row=0, column=0, padx=4)
            quick_toggle = ctk.CTkButton(btn_frame, text="🔄", width=48, height=36, command=lambda t=task: self.open_toggle_dialog(t))
            quick_toggle.grid(row=0, column=1, padx=4)
            quick_delete = ctk.CTkButton(btn_frame, text="🗑️", width=48, height=36, command=lambda t=task: self.open_delete_dialog(t))
            quick_delete.grid(row=0, column=2, padx=4)

            # apply status background if any (non-selected)
            try:
                if row_bg:
                    row_frame.configure(fg_color=row_bg)
                else:
                    row_frame.configure(fg_color=None)
            except Exception:
                pass

            # if this task is selected, override background and text color for readability
            if self.selected_task_id == task["id"]:
                try:
                    # choose a selection background that contrasts with mode
                    if appearance == "dark":
                        sel_bg = "#cfe8ff"  # light blue
                        sel_text = "black"
                    else:
                        sel_bg = "#2f74c0"  # darker blue for light mode
                        sel_text = "white"
                    row_frame.configure(fg_color=sel_bg)
                    lbl.configure(text_color=sel_text)
                except Exception:
                    pass
            else:
                # ensure label has default text color (non-selected)
                lbl.configure(text_color=default_text_color)

            # bind click selection on entire row (toggle on second click)
            row_frame.bind("<Button-1>", lambda e, t=task: self.select_row(t))
            lbl.bind("<Button-1>", lambda e, t=task: self.select_row(t))

        # update selected label
        self.update_selected_label()

    # selection helpers (TOGGLE behavior implemented)
    def select_row(self, task):
        # toggle selection: if clicked again, unselect
        if self.selected_task_id == task["id"]:
            self.selected_task_id = None
        else:
            self.selected_task_id = task["id"]
        # refresh to update visuals
        self.refresh_list()

    def update_selected_label(self):
        if self.selected_task_id is None:
            self.selected_label.configure(text="Selected: None")
        else:
            t = next((x for x in self.tasks if x["id"] == self.selected_task_id), None)
            if t:
                self.selected_label.configure(text=f"Selected: ID {t['id']} - {t['task'][:40]}")
            else:
                self.selected_label.configure(text="Selected: None")

    # quick dialog openers used by quick buttons
    def open_update_dialog(self, task):
        UpdateTaskDialog(self, task, lambda _: (save_tasks(self.tasks), self.refresh_list()))

    def open_delete_dialog(self, task):
        DeleteTaskDialog(self, task, lambda t: (self.tasks.remove(t), save_tasks(self.tasks), self.refresh_list()))

    def open_toggle_dialog(self, task):
        ToggleTaskDialog(self, task, lambda t: (self._toggle(t), save_tasks(self.tasks), self.refresh_list()))

    # standard footer actions operate on selected task (no ID typing)
    def update_task(self):
        if self.selected_task_id is None:
            messagebox.showinfo("No Selection", "Please click a task row to select it first.")
            return
        task = next((t for t in self.tasks if t["id"] == self.selected_task_id), None)
        if not task:
            messagebox.showinfo("Not Found", "Selected task not found.")
            return
        UpdateTaskDialog(self, task, lambda _: (save_tasks(self.tasks), self.refresh_list()))

    def delete_task(self):
        if self.selected_task_id is None:
            messagebox.showinfo("No Selection", "Please click a task row to select it first.")
            return
        task = next((t for t in self.tasks if t["id"] == self.selected_task_id), None)
        if not task:
            messagebox.showinfo("Not Found", "Selected task not found.")
            return
        DeleteTaskDialog(self, task, lambda t: (self.tasks.remove(t), save_tasks(self.tasks), self.refresh_list(), self.clear_selection()))

    def toggle_completion(self):
        if self.selected_task_id is None:
            messagebox.showinfo("No Selection", "Please click a task row to select it first.")
            return
        task = next((t for t in self.tasks if t["id"] == self.selected_task_id), None)
        if not task:
            messagebox.showinfo("Not Found", "Selected task not found.")
            return
        ToggleTaskDialog(self, task, lambda t: (self._toggle(t), save_tasks(self.tasks), self.refresh_list()))

    def _toggle(self, task):
        task["completed"] = not task["completed"]

    def clear_selection(self):
        self.selected_task_id = None
        self.refresh_list()

    # Add task
    def add_task(self):
        new_task = self.task_entry.get().strip()
        due_date = self.due_date_var.get().strip()
        if not new_task:
            messagebox.showwarning("Invalid Input", "Task cannot be empty.")
            return
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except Exception:
            messagebox.showwarning("Invalid Date", "Please select a valid due date.")
            return
        task = {"id": generate_task_id(self.tasks), "task": new_task, "completed": False, "due_date": due_date}
        self.tasks.append(task)
        save_tasks(self.tasks)
        self.task_entry.delete(0, "end")
        self.due_date_var.set(datetime.today().strftime("%Y-%m-%d"))
        self.refresh_list()

    # Import/Export implementations
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], title="Export tasks to CSV")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id","task","completed","due_date"])
                for t in self.tasks:
                    writer.writerow([t["id"], t["task"], t["completed"], t.get("due_date","No due date")])
            messagebox.showinfo("Exported", f"Tasks exported to CSV:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def export_excel(self):
        if not PANDAS_AVAILABLE:
            # fall back: export CSV and inform user
            res = messagebox.askyesno("Pandas not installed", "Pandas/openpyxl are required for Excel export. Export CSV instead?")
            if res:
                self.export_csv()
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files","*.xlsx")], title="Export tasks to Excel")
        if not path:
            return
        try:
            df = pd.DataFrame(self.tasks)
            # ensure columns order
            df = df[["id","task","completed","due_date"]]
            df.to_excel(path, index=False)
            messagebox.showinfo("Exported", f"Tasks exported to Excel:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files","*.csv")], title="Import tasks from CSV")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                added = 0
                for row in reader:
                    # map fields, handle missing/invalid
                    txt = row.get("task") or row.get("Task") or ""
                    if not txt.strip():
                        continue
                    comp_field = row.get("completed","False")
                    completed = str(comp_field).strip().lower() in ("1","true","yes","y","t")
                    due = row.get("due_date") or row.get("Due Date") or "No due date"
                    # avoid id collisions: assign new ID
                    task = {"id": generate_task_id(self.tasks), "task": txt.strip(), "completed": completed, "due_date": due}
                    self.tasks.append(task)
                    added += 1
                save_tasks(self.tasks)
                messagebox.showinfo("Import Complete", f"Imported {added} tasks from CSV.")
                self.refresh_list()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    # Startup reminder: show tasks due today
    def startup_reminder(self):
        today = date.today()
        due_today = [t for t in self.tasks if (t.get("due_date") and t["due_date"] != "No due date" and \
                    (lambda d: (d == today))(datetime.strptime(t["due_date"], "%Y-%m-%d").date()) and not t["completed"])]
        if due_today:
            text = "Tasks due today:\n\n" + "\n".join([f"ID {t['id']}: {t['task']}" for t in due_today])
            # show a non-blocking popup (messagebox is blocking, but OK at startup)
            messagebox.showinfo("Due Today", text)

    def ask_for_id_old(self, title):
        # kept for compatibility if user wants old behavior; not used by default
        dialog = ctk.CTkInputDialog(text=title, title=title)
        try:
            return int(dialog.get_input()) if dialog.get_input() else None
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid numeric ID.")
            return None

    def change_mode(self):
        mode = self.switch_var.get()
        ctk.set_appearance_mode(mode)
        # re-render to make sure colors adapt
        self.refresh_list()

# Run
if __name__ == "__main__":
    app = TaskManagerApp()
    app.mainloop()
