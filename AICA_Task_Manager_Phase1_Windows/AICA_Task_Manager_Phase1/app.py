"""
AICA's Task Manager - Phase 1
Windows desktop application using Python Tkinter + SQLite.
Run: python app.py
Default login: admin / Admin@12345
Change the default password after first login.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3, hashlib, secrets, os
from datetime import date, datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "aica_tasks.db")
ROLES = ["Admin", "Partner", "Manager", "Accountant", "Paid Assistant", "Article"]
STATUSES = ["Pending", "In Progress", "Under Review", "Completed"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180000).hex()
    return salt, digest

def verify_password(password, salt, digest):
    return secrets.compare_digest(hash_password(password, salt)[1], digest)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.setup()

    def setup(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            client_name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Pending',
            assigned_to INTEGER,
            created_by INTEGER,
            start_date TEXT DEFAULT '',
            due_date TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(assigned_to) REFERENCES users(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS task_updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS activity_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)
        row = self.conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not row:
            salt, digest = hash_password("Admin@12345")
            self.conn.execute(
                "INSERT INTO users(full_name,username,password_salt,password_hash,role) VALUES(?,?,?,?,?)",
                ("System Administrator", "admin", salt, digest, "Admin"))
        self.conn.commit()

    def log(self, user_id, action, details=""):
        self.conn.execute("INSERT INTO activity_logs(user_id,action,details) VALUES(?,?,?)",
                          (user_id, action, details))
        self.conn.commit()

    def authenticate(self, username, password):
        row = self.conn.execute("SELECT * FROM users WHERE username=? AND active=1",
                                (username.strip(),)).fetchone()
        if row and verify_password(password, row["password_salt"], row["password_hash"]):
            return row
        return None

    def users(self, active_only=True):
        q = "SELECT * FROM users" + (" WHERE active=1" if active_only else "") + " ORDER BY full_name"
        return self.conn.execute(q).fetchall()

    def save_user(self, data, user_id=None):
        if user_id:
            if data.get("password"):
                salt, digest = hash_password(data["password"])
                self.conn.execute("""UPDATE users SET full_name=?,username=?,role=?,email=?,
                    password_salt=?,password_hash=? WHERE id=?""",
                    (data["full_name"], data["username"], data["role"], data["email"], salt, digest, user_id))
            else:
                self.conn.execute("UPDATE users SET full_name=?,username=?,role=?,email=? WHERE id=?",
                    (data["full_name"], data["username"], data["role"], data["email"], user_id))
        else:
            salt, digest = hash_password(data["password"])
            self.conn.execute("""INSERT INTO users(full_name,username,password_salt,password_hash,role,email)
                VALUES(?,?,?,?,?,?)""",
                (data["full_name"], data["username"], salt, digest, data["role"], data["email"]))
        self.conn.commit()

    def deactivate_user(self, user_id):
        self.conn.execute("UPDATE users SET active=0 WHERE id=?", (user_id,))
        self.conn.commit()

    def tasks(self, user):
        role = user["role"]
        if role in ("Admin", "Partner", "Manager"):
            return self.conn.execute("""SELECT t.*,u.full_name assignee FROM tasks t
                LEFT JOIN users u ON u.id=t.assigned_to ORDER BY
                CASE t.status WHEN 'Pending' THEN 1 WHEN 'In Progress' THEN 2
                WHEN 'Under Review' THEN 3 ELSE 4 END, t.due_date""").fetchall()
        return self.conn.execute("""SELECT t.*,u.full_name assignee FROM tasks t
            LEFT JOIN users u ON u.id=t.assigned_to WHERE t.assigned_to=?
            ORDER BY t.due_date""", (user["id"],)).fetchall()

    def save_task(self, data, actor_id, task_id=None):
        if task_id:
            old = self.conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            self.conn.execute("""UPDATE tasks SET title=?,client_name=?,description=?,priority=?,
                status=?,assigned_to=?,start_date=?,due_date=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (data["title"],data["client_name"],data["description"],data["priority"],data["status"],
                 data["assigned_to"],data["start_date"],data["due_date"],task_id))
            if old and old["status"] != data["status"]:
                self.conn.execute("""INSERT INTO task_updates(task_id,user_id,old_status,new_status,note)
                    VALUES(?,?,?,?,?)""", (task_id,actor_id,old["status"],data["status"],"Status updated"))
        else:
            cur = self.conn.execute("""INSERT INTO tasks(title,client_name,description,priority,status,
                assigned_to,created_by,start_date,due_date) VALUES(?,?,?,?,?,?,?,?,?)""",
                (data["title"],data["client_name"],data["description"],data["priority"],data["status"],
                 data["assigned_to"],actor_id,data["start_date"],data["due_date"]))
            task_id = cur.lastrowid
            self.conn.execute("""INSERT INTO task_updates(task_id,user_id,old_status,new_status,note)
                VALUES(?,?,?,?,?)""", (task_id,actor_id,"",data["status"],"Task created"))
        self.conn.commit()
        self.log(actor_id, "Task saved", f"Task ID {task_id}: {data['title']}")

    def delete_task(self, task_id, actor_id):
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()
        self.log(actor_id, "Task deleted", f"Task ID {task_id}")

    def stats(self, user):
        rows = self.tasks(user)
        today = date.today().isoformat()
        return {
            "Total": len(rows),
            "Pending": sum(r["status"] == "Pending" for r in rows),
            "In Progress": sum(r["status"] == "In Progress" for r in rows),
            "Completed": sum(r["status"] == "Completed" for r in rows),
            "Overdue": sum(bool(r["due_date"]) and r["due_date"] < today and r["status"] != "Completed" for r in rows)
        }

class LoginWindow:
    def __init__(self, root, db):
        self.root, self.db = root, db
        root.title("AICA's Task Manager | Login")
        root.geometry("430x390")
        root.resizable(False, False)
        root.configure(bg="#edf2f7")
        card = tk.Frame(root, bg="white", padx=34, pady=28, highlightthickness=1, highlightbackground="#d9e2ec")
        card.place(relx=.5, rely=.5, anchor="center", width=350, height=320)
        tk.Label(card, text="AICA", font=("Segoe UI", 25, "bold"), fg="#17436b", bg="white").pack()
        tk.Label(card, text="TASK MANAGER", font=("Segoe UI", 10, "bold"), fg="#60758a", bg="white").pack(pady=(0,18))
        tk.Label(card, text="Username", bg="white", fg="#34495e").pack(anchor="w")
        self.username = ttk.Entry(card, font=("Segoe UI", 11))
        self.username.pack(fill="x", pady=(4,12))
        tk.Label(card, text="Password", bg="white", fg="#34495e").pack(anchor="w")
        self.password = ttk.Entry(card, show="●", font=("Segoe UI", 11))
        self.password.pack(fill="x", pady=(4,18))
        ttk.Button(card, text="Sign In", command=self.login).pack(fill="x", ipady=5)
        tk.Label(card, text="Default: admin / Admin@12345", bg="white", fg="#8494a5",
                 font=("Segoe UI", 8)).pack(pady=12)
        self.password.bind("<Return>", lambda e: self.login())
        self.username.focus_set()

    def login(self):
        user = self.db.authenticate(self.username.get(), self.password.get())
        if not user:
            messagebox.showerror("Login failed", "Invalid username or password, or account is inactive.")
            return
        self.db.log(user["id"], "Login", "Successful login")
        for w in self.root.winfo_children(): w.destroy()
        MainWindow(self.root, self.db, user)

class MainWindow:
    def __init__(self, root, db, user):
        self.root, self.db, self.user = root, db, user
        root.title("AICA's Task Manager")
        root.geometry("1180x760")
        root.minsize(960, 620)
        root.configure(bg="#f3f6fa")
        self.style = ttk.Style()
        try: self.style.theme_use("clam")
        except: pass
        self.style.configure("Treeview", rowheight=30, font=("Segoe UI", 9), background="white", fieldbackground="white")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e8eef5")
        self.style.configure("TButton", font=("Segoe UI", 9))
        self.build_shell()
        self.show_dashboard()

    def build_shell(self):
        header = tk.Frame(self.root, bg="#173f63", height=66)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="AICA's TASK MANAGER", bg="#173f63", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=24)
        tk.Label(header, text=f"{self.user['full_name']}  |  {self.user['role']}",
                 bg="#173f63", fg="#dce8f3", font=("Segoe UI", 10)).pack(side="right", padx=22)
        body = tk.Frame(self.root, bg="#f3f6fa")
        body.pack(fill="both", expand=True)
        nav = tk.Frame(body, bg="#214e73", width=205)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        tk.Label(nav, text="WORKSPACE", bg="#214e73", fg="#a9c2d8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(22,10))
        self.nav_button(nav, "▦   Dashboard", self.show_dashboard)
        self.nav_button(nav, "☷   Task Register", self.show_tasks)
        if self.user["role"] == "Admin":
            self.nav_button(nav, "♙   User Management", self.show_users)
        tk.Frame(nav, bg="#52718d", height=1).pack(fill="x", padx=15, pady=18)
        self.nav_button(nav, "↻   Refresh", self.refresh)
        self.nav_button(nav, "⇥   Logout", self.logout)
        self.content = tk.Frame(body, bg="#f3f6fa", padx=25, pady=22)
        self.content.pack(side="left", fill="both", expand=True)

    def nav_button(self, parent, text, command):
        b = tk.Button(parent, text=text, command=command, anchor="w", padx=18, pady=11,
                      relief="flat", bd=0, bg="#214e73", fg="white",
                      activebackground="#2e638e", activeforeground="white",
                      font=("Segoe UI", 10), cursor="hand2")
        b.pack(fill="x", padx=7, pady=2)

    def clear(self):
        for w in self.content.winfo_children(): w.destroy()

    def title(self, heading, subtitle=""):
        tk.Label(self.content, text=heading, bg="#f3f6fa", fg="#183b59",
                 font=("Segoe UI", 21, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(self.content, text=subtitle, bg="#f3f6fa", fg="#708397",
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(2,16))

    def show_dashboard(self):
        self.clear()
        self.title("Dashboard", f"Welcome, {self.user['full_name']}  •  {date.today().strftime('%d %B %Y')}")
        stats = self.db.stats(self.user)
        cards = tk.Frame(self.content, bg="#f3f6fa")
        cards.pack(fill="x", pady=(0,20))
        colors = ["#ffffff","#fff8e8","#edf5fc","#eaf7f0","#fff0ef"]
        for i, (label, value) in enumerate(stats.items()):
            card = tk.Frame(cards, bg=colors[i], padx=17, pady=14, highlightthickness=1, highlightbackground="#e0e7ef")
            card.grid(row=0, column=i, sticky="nsew", padx=(0,10))
            cards.grid_columnconfigure(i, weight=1)
            tk.Label(card, text=label.upper(), bg=colors[i], fg="#6d8194",
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(card, text=str(value), bg=colors[i], fg="#183b59",
                     font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(4,0))
        section = tk.Frame(self.content, bg="white", padx=16, pady=14, highlightthickness=1, highlightbackground="#e0e7ef")
        section.pack(fill="both", expand=True)
        tk.Label(section, text="Tasks Requiring Attention", bg="white", fg="#183b59",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0,10))
        rows = [r for r in self.db.tasks(self.user) if r["status"] != "Completed"]
        rows = rows[:8]
        cols = ("title","client_name","assignee","priority","status","due_date")
        tree = ttk.Treeview(section, columns=cols, show="headings", height=10)
        heads = {"title":"Task","client_name":"Client","assignee":"Assigned To","priority":"Priority","status":"Status","due_date":"Due Date"}
        widths = {"title":250,"client_name":145,"assignee":130,"priority":85,"status":120,"due_date":100}
        for c in cols:
            tree.heading(c, text=heads[c]); tree.column(c, width=widths[c], anchor="w")
        for r in rows:
            tree.insert("", "end", values=tuple(r[c] or "" for c in cols))
        tree.pack(fill="both", expand=True)
        if not rows:
            tk.Label(section, text="No open tasks. Great work!", bg="white", fg="#71869a").pack(pady=10)
        ttk.Button(self.content, text="Open Task Register", command=self.show_tasks).pack(anchor="e", pady=12)

    def show_tasks(self):
        self.clear()
        self.title("Task Register", "Create, allocate and monitor work across the firm.")
        toolbar = tk.Frame(self.content, bg="#f3f6fa")
        toolbar.pack(fill="x", pady=(0,10))
        if self.user["role"] in ("Admin","Partner","Manager"):
            ttk.Button(toolbar, text="+  New Task", command=lambda: self.task_dialog()).pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=34)
        search.pack(side="right", padx=(5,0))
        ttk.Button(toolbar, text="Search", command=self.populate_tasks).pack(side="right")
        self.search_var.trace_add("write", lambda *_: self.populate_tasks())
        frame = tk.Frame(self.content, bg="white", padx=10, pady=10)
        frame.pack(fill="both", expand=True)
        cols = ("id","title","client_name","assignee","priority","status","due_date")
        self.task_tree = ttk.Treeview(frame, columns=cols, show="headings")
        heads = {"id":"ID","title":"Task","client_name":"Client","assignee":"Assigned To","priority":"Priority","status":"Status","due_date":"Due Date"}
        widths = {"id":45,"title":250,"client_name":150,"assignee":140,"priority":85,"status":120,"due_date":100}
        for c in cols:
            self.task_tree.heading(c, text=heads[c]); self.task_tree.column(c, width=widths[c], anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=yscroll.set)
        self.task_tree.pack(side="left", fill="both", expand=True); yscroll.pack(side="right", fill="y")
        actions = tk.Frame(self.content, bg="#f3f6fa")
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="View / Update Selected", command=self.edit_selected).pack(side="left")
        if self.user["role"] in ("Admin","Partner"):
            ttk.Button(actions, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=8)
        self.populate_tasks()

    def populate_tasks(self):
        if not hasattr(self, "task_tree") or not self.task_tree.winfo_exists(): return
        for item in self.task_tree.get_children(): self.task_tree.delete(item)
        term = self.search_var.get().lower() if hasattr(self, "search_var") else ""
        for r in self.db.tasks(self.user):
            values = [r["id"],r["title"],r["client_name"],r["assignee"],r["priority"],r["status"],r["due_date"]]
            if term and not any(term in str(v or "").lower() for v in values): continue
            self.task_tree.insert("", "end", iid=str(r["id"]), values=values)

    def selected_task(self):
        sel = self.task_tree.selection()
        if not sel:
            messagebox.showinfo("Select task", "Please select a task first."); return None
        return self.db.conn.execute("SELECT * FROM tasks WHERE id=?", (int(sel[0]),)).fetchone()

    def edit_selected(self):
        row = self.selected_task()
        if not row: return
        can_manage = self.user["role"] in ("Admin","Partner","Manager")
        if not can_manage and row["assigned_to"] != self.user["id"]:
            messagebox.showerror("Permission denied", "You can only update tasks assigned to you."); return
        self.task_dialog(row)

    def delete_selected(self):
        row = self.selected_task()
        if not row: return
        if messagebox.askyesno("Confirm deletion", f"Delete task '{row['title']}'?"):
            self.db.delete_task(row["id"], self.user["id"])
            self.populate_tasks()

    def task_dialog(self, row=None):
        can_manage = self.user["role"] in ("Admin","Partner","Manager")
        win = tk.Toplevel(self.root); win.title("Task Details"); win.geometry("540x610"); win.transient(self.root); win.grab_set()
        win.configure(bg="white")
        pad = tk.Frame(win, bg="white", padx=24, pady=18); pad.pack(fill="both", expand=True)
        tk.Label(pad, text="Edit Task" if row else "Create New Task", bg="white", fg="#183b59",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", pady=(0,14))
        fields = {}
        def field(label, key, default="", values=None, state="normal"):
            tk.Label(pad, text=label, bg="white", fg="#53697d", font=("Segoe UI",9,"bold")).pack(anchor="w", pady=(6,2))
            if values:
                v = tk.StringVar(value=default)
                w = ttk.Combobox(pad, textvariable=v, values=values, state="readonly")
            else:
                v = tk.StringVar(value=default)
                w = ttk.Entry(pad, textvariable=v, state=state)
            w.pack(fill="x", ipady=3)
            fields[key] = v
        field("Task Title *","title",row["title"] if row else "")
        field("Client / Entity","client_name",row["client_name"] if row else "")
        tk.Label(pad, text="Description", bg="white", fg="#53697d", font=("Segoe UI",9,"bold")).pack(anchor="w", pady=(6,2))
        desc = tk.Text(pad, height=4, font=("Segoe UI",9), relief="solid", bd=1); desc.pack(fill="x")
        if row: desc.insert("1.0", row["description"] or "")
        field("Priority","priority",row["priority"] if row else "Medium",PRIORITIES)
        field("Status","status",row["status"] if row else "Pending",STATUSES)
        users = self.db.users()
        user_map = {f"{u['full_name']} ({u['role']})":u["id"] for u in users}
        current_assignee = ""
        if row:
            for label, uid in user_map.items():
                if uid == row["assigned_to"]: current_assignee = label
        if can_manage:
            field("Assigned To","assigned_to",current_assignee,list(user_map.keys()))
        else:
            fields["assigned_to"] = tk.StringVar(value=current_assignee)
        field("Start Date (YYYY-MM-DD)","start_date",row["start_date"] if row else date.today().isoformat())
        field("Due Date (YYYY-MM-DD)","due_date",row["due_date"] if row else "")
        def save():
            data = {k:v.get().strip() for k,v in fields.items()}
            data["description"] = desc.get("1.0","end").strip()
            if not data["title"]:
                messagebox.showerror("Required", "Task title is required.", parent=win); return
            for key in ("start_date","due_date"):
                if data[key]:
                    try: datetime.strptime(data[key], "%Y-%m-%d")
                    except ValueError:
                        messagebox.showerror("Invalid date", f"{key.replace('_',' ').title()} must be YYYY-MM-DD.", parent=win); return
            if can_manage:
                data["assigned_to"] = user_map.get(data["assigned_to"])
            else:
                data["assigned_to"] = self.user["id"]
                data["status"] = fields["status"].get()
            if not data["assigned_to"]:
                messagebox.showerror("Assignee required", "Please select an employee.", parent=win); return
            self.db.save_task(data,self.user["id"],row["id"] if row else None)
            win.destroy()
            self.refresh()
        ttk.Button(pad, text="Save Task", command=save).pack(anchor="e", pady=16, ipadx=14, ipady=4)

    def show_users(self):
        if self.user["role"] != "Admin": return
        self.clear()
        self.title("User Management", "Only the system administrator can create and manage user accounts.")
        bar = tk.Frame(self.content, bg="#f3f6fa"); bar.pack(fill="x", pady=(0,10))
        ttk.Button(bar, text="+  Add User", command=lambda: self.user_dialog()).pack(side="left")
        frame = tk.Frame(self.content, bg="white", padx=10, pady=10); frame.pack(fill="both", expand=True)
        cols=("id","full_name","username","role","email","active")
        tree=ttk.Treeview(frame,columns=cols,show="headings")
        labels=("ID","Full Name","Username","Role","Email","Active")
        widths=(50,220,150,150,230,70)
        for c,l,w in zip(cols,labels,widths): tree.heading(c,text=l); tree.column(c,width=w,anchor="w")
        for u in self.db.users(active_only=False):
            tree.insert("","end",iid=str(u["id"]),values=(u["id"],u["full_name"],u["username"],u["role"],u["email"],"Yes" if u["active"] else "No"))
        tree.pack(fill="both",expand=True)
        self.user_tree=tree
        actions=tk.Frame(self.content,bg="#f3f6fa"); actions.pack(fill="x",pady=10)
        ttk.Button(actions,text="Edit Selected",command=self.edit_user_selected).pack(side="left")
        ttk.Button(actions,text="Deactivate Selected",command=self.deactivate_selected).pack(side="left",padx=8)

    def user_dialog(self, row=None):
        win=tk.Toplevel(self.root); win.title("User Details"); win.geometry("430x430"); win.transient(self.root); win.grab_set()
        pad=tk.Frame(win,bg="white",padx=24,pady=20);pad.pack(fill="both",expand=True)
        tk.Label(pad,text="Edit User" if row else "Add User",font=("Segoe UI",17,"bold"),bg="white",fg="#183b59").pack(anchor="w",pady=(0,12))
        vars={}
        def add(label,key,default="",values=None):
            tk.Label(pad,text=label,bg="white",fg="#53697d").pack(anchor="w",pady=(7,2))
            v=tk.StringVar(value=default)
            w=ttk.Combobox(pad,textvariable=v,values=values,state="readonly") if values else ttk.Entry(pad,textvariable=v)
            w.pack(fill="x",ipady=3);vars[key]=v
        add("Full Name *","full_name",row["full_name"] if row else "")
        add("Username *","username",row["username"] if row else "")
        add("Role","role",row["role"] if row else "Article",ROLES[1:])
        add("Email","email",row["email"] if row else "")
        add("Password *" if not row else "New Password (leave blank to retain)","password","")
        def save():
            d={k:v.get().strip() for k,v in vars.items()}
            if not d["full_name"] or not d["username"] or (not row and not d["password"]):
                messagebox.showerror("Required","Name, username and password are required.",parent=win);return
            try:
                self.db.save_user(d,row["id"] if row else None)
            except sqlite3.IntegrityError:
                messagebox.showerror("Duplicate username","That username is already in use.",parent=win);return
            self.db.log(self.user["id"],"User saved",d["username"])
            win.destroy();self.show_users()
        ttk.Button(pad,text="Save User",command=save).pack(anchor="e",pady=18)

    def edit_user_selected(self):
        sel=self.user_tree.selection()
        if not sel: messagebox.showinfo("Select user","Select a user first.");return
        row=self.db.conn.execute("SELECT * FROM users WHERE id=?",(int(sel[0]),)).fetchone()
        self.user_dialog(row)

    def deactivate_selected(self):
        sel=self.user_tree.selection()
        if not sel: messagebox.showinfo("Select user","Select a user first.");return
        uid=int(sel[0])
        if uid==self.user["id"]:
            messagebox.showerror("Not allowed","You cannot deactivate your own account.");return
        if messagebox.askyesno("Confirm","Deactivate this user?"):
            self.db.deactivate_user(uid);self.show_users()

    def refresh(self):
        self.show_dashboard()

    def logout(self):
        self.db.log(self.user["id"],"Logout","User logged out")
        for w in self.root.winfo_children(): w.destroy()
        LoginWindow(self.root,self.db)

def main():
    root=tk.Tk()
    db=Database()
    LoginWindow(root,db)
    root.mainloop()

if __name__ == "__main__":
    main()
