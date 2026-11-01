# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import random
from datetime import datetime

# -----------------------------------------
# DATABASE SETUP
# -----------------------------------------

conn = sqlite3.connect("question_analyzer.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    chapter TEXT NOT NULL,
    question TEXT NOT NULL,
    marks INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    year TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    chapter TEXT NOT NULL,
    obtained REAL NOT NULL,
    total REAL NOT NULL,
    test_date TEXT NOT NULL
)
""")

conn.commit()


# -----------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------

def get_values(query, params=()):
    cursor.execute(query, params)
    return cursor.fetchall()


def get_subjects():
    return sorted({
        row[0] for row in get_values(
            "SELECT DISTINCT subject FROM questions"
        )
    })


def get_chapters(subject):
    return sorted({
        row[0] for row in get_values(
            "SELECT DISTINCT chapter FROM questions "
            "WHERE subject = ?", (subject,)
        )
    })


def refresh_status():
    question_count = get_values(
        "SELECT COUNT(*) FROM questions"
    )[0][0]

    test_count = get_values(
        "SELECT COUNT(*) FROM scores"
    )[0][0]

    status_label.config(
        text=f"Questions stored: {question_count}    |    "
             f"Score records: {test_count}"
    )


# -----------------------------------------
# ADD QUESTIONS
# -----------------------------------------

def add_question():
    win = tk.Toplevel(root)
    win.title("Add a Question")
    win.geometry("480x490")
    win.resizable(False, False)

    fields = {}

    labels = [
        "Subject",
        "Chapter",
        "Question",
        "Marks",
        "Difficulty",
        "Year"
    ]

    for i, label in enumerate(labels):
        ttk.Label(
            win, text=label + ":"
        ).grid(row=i, column=0, padx=12, pady=10, sticky="w")

        if label == "Difficulty":
            widget = ttk.Combobox(
                win,
                values=["Easy", "Medium", "Hard"],
                state="readonly",
                width=32
            )
            widget.set("Medium")

        elif label == "Question":
            widget = tk.Text(win, width=34, height=4)

        else:
            widget = ttk.Entry(win, width=35)

        widget.grid(
            row=i, column=1, padx=12, pady=8, sticky="ew"
        )
        fields[label] = widget

    def save():
        subject = fields["Subject"].get().strip()
        chapter = fields["Chapter"].get().strip()
        question_widget = fields["Question"]
        question = question_widget.get("1.0", "end").strip()
        marks_text = fields["Marks"].get().strip()
        difficulty = fields["Difficulty"].get()
        year = fields["Year"].get().strip()

        if not subject or not chapter or not question:
            messagebox.showerror(
                "Missing information",
                "Enter the subject, chapter, and question.",
                parent=win
            )
            return

        try:
            marks = int(marks_text)
            if marks <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid marks",
                "Marks must be a positive whole number.",
                parent=win
            )
            return

        cursor.execute("""
            INSERT INTO questions
            (subject, chapter, question, marks, difficulty, year)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (subject, chapter, question, marks, difficulty, year))

        conn.commit()
        refresh_status()

        messagebox.showinfo(
            "Success", "Question saved successfully!", parent=win
        )
        win.destroy()

    ttk.Button(
        win, text="Save Question", command=save
    ).grid(row=6, column=0, columnspan=2, pady=20)


# -----------------------------------------
# VIEW QUESTION BANK
# -----------------------------------------

def view_questions():
    win = tk.Toplevel(root)
    win.title("Question Bank")
    win.geometry("950x430")

    columns = (
        "ID", "Subject", "Chapter",
        "Question", "Marks", "Difficulty", "Year"
    )

    tree = ttk.Treeview(
        win, columns=columns, show="headings"
    )

    widths = [45, 110, 110, 330, 55, 90, 65]

    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=width)

    scrollbar = ttk.Scrollbar(
        win, orient="vertical", command=tree.yview
    )
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for row in get_values("""
        SELECT id, subject, chapter, question,
               marks, difficulty, year
        FROM questions ORDER BY subject, chapter, id
    """):
        tree.insert("", "end", values=row)


# -----------------------------------------
# GENERATE PRACTICE PAPER
# -----------------------------------------

def generate_paper():
    win = tk.Toplevel(root)
    win.title("Practice Paper Generator")
    win.geometry("650x590")

    subjects = get_subjects()

    if not subjects:
        messagebox.showwarning(
            "Empty question bank",
            "Add some questions before generating a paper.",
            parent=win
        )
        win.destroy()
        return

    ttk.Label(win, text="Subject:").pack(pady=(12, 3))

    subject_box = ttk.Combobox(
        win, values=subjects, state="readonly", width=35
    )
    subject_box.pack()
    subject_box.current(0)

    ttk.Label(
        win, text="Chapters (leave empty to use all chapters):"
    ).pack(pady=(12, 3))

    chapter_box = tk.Listbox(
        win, selectmode=tk.MULTIPLE, height=5,
        exportselection=False
    )
    chapter_box.pack(fill="x", padx=25)

    def update_chapters(event=None):
        chapter_box.delete(0, tk.END)
        for chapter in get_chapters(subject_box.get()):
            chapter_box.insert(tk.END, chapter)

    subject_box.bind("<<ComboboxSelected>>", update_chapters)
    update_chapters()

    ttk.Label(win, text="Difficulty:").pack(pady=(12, 3))

    difficulty_box = ttk.Combobox(
        win,
        values=["Any", "Easy", "Medium", "Hard"],
        state="readonly",
        width=35
    )
    difficulty_box.set("Any")
    difficulty_box.pack()

    ttk.Label(win, text="Target total marks:").pack(pady=(12, 3))

    marks_entry = ttk.Entry(win, width=15)
    marks_entry.insert(0, "20")
    marks_entry.pack()

    output = tk.Text(win, height=12, wrap="word")
    output.pack(fill="both", expand=True, padx=12, pady=12)

    def create_paper():
        subject = subject_box.get()
        selected = [
            chapter_box.get(i)
            for i in chapter_box.curselection()
        ]
        difficulty = difficulty_box.get()

        try:
            target = int(marks_entry.get())
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid marks",
                "Enter a positive whole number for target marks.",
                parent=win
            )
            return

        query = """
            SELECT chapter, question, marks, difficulty, year
            FROM questions WHERE subject = ?
        """
        params = [subject]

        if selected:
            placeholders = ",".join("?" for _ in selected)
            query += f" AND chapter IN ({placeholders})"
            params.extend(selected)

        if difficulty != "Any":
            query += " AND difficulty = ?"
            params.append(difficulty)

        available = get_values(query, tuple(params))
        random.shuffle(available)

        chosen = []
        total = 0

        # Select questions without exceeding the target.
        for item in available:
            if total + item[2] <= target:
                chosen.append(item)
                total += item[2]

        output.delete("1.0", tk.END)

        if not chosen:
            output.insert(
                tk.END,
                "No questions fit the selected criteria and marks.\n"
                "Try a higher target or different filters."
            )
            return

        lines = [
            "PREVIOUS QUESTION PAPER",
            "=" * 35,
            f"Subject: {subject}",
            f"Maximum target marks: {target}",
            f"Selected questions total: {total}",
            "",
        ]

        for i, (chapter, question, marks, level, year) in enumerate(
            chosen, start=1
        ):
            lines.extend([
                f"{i}. [{chapter}] {question}",
                f"   Marks: {marks} | Difficulty: {level}"
                + (f" | Year: {year}" if year else ""),
                ""
            ])

        if total < target:
            lines.append(
                "Note: The available questions could not fill "
                "the entire target."
            )

        output.insert(tk.END, "\n".join(lines))

    ttk.Button(
        win, text="Generate Paper", command=create_paper
    ).pack(pady=(0, 12))


# -----------------------------------------
# RECORD TEST SCORES
# -----------------------------------------

def record_score():
    win = tk.Toplevel(root)
    win.title("Record Test Score")
    win.geometry("430x350")

    subjects = get_subjects()

    if not subjects:
        messagebox.showwarning(
            "Empty question bank",
            "Add questions before recording scores.",
            parent=win
        )
        win.destroy()
        return

    ttk.Label(win, text="Subject:").pack(pady=(12, 3))

    subject_box = ttk.Combobox(
        win, values=subjects, state="readonly", width=30
    )
    subject_box.pack()
    subject_box.current(0)

    ttk.Label(win, text="Chapter:").pack(pady=(10, 3))

    chapter_box = ttk.Combobox(
        win, state="readonly", width=30
    )
    chapter_box.pack()

    def update_chapters(event=None):
        chapter_box["values"] = get_chapters(subject_box.get())
        if chapter_box["values"]:
            chapter_box.current(0)

    subject_box.bind("<<ComboboxSelected>>", update_chapters)
    update_chapters()

    ttk.Label(win, text="Marks obtained:").pack(pady=(10, 3))
    obtained_entry = ttk.Entry(win, width=20)
    obtained_entry.pack()

    ttk.Label(win, text="Total marks:").pack(pady=(10, 3))
    total_entry = ttk.Entry(win, width=20)
    total_entry.pack()

    def save_score():
        subject = subject_box.get()
        chapter = chapter_box.get()

        try:
            obtained = float(obtained_entry.get())
            total = float(total_entry.get())

            if total <= 0 or obtained < 0 or obtained > total:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid score",
                "Enter valid marks: obtained must be between "
                "zero and total marks.",
                parent=win
            )
            return

        if not chapter:
            messagebox.showerror(
                "Missing chapter", "Select a chapter.", parent=win
            )
            return

        cursor.execute("""
            INSERT INTO scores
            (subject, chapter, obtained, total, test_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            subject, chapter, obtained, total,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        conn.commit()
        refresh_status()

        messagebox.showinfo(
            "Saved", "Test score recorded successfully!", parent=win
        )
        win.destroy()

    ttk.Button(
        win, text="Save Score", command=save_score
    ).pack(pady=18)


# -----------------------------------------
# CHAPTER-WISE PERFORMANCE ANALYSIS
# -----------------------------------------

def analyze_performance():
    rows = get_values("""
        SELECT subject, chapter,
               SUM(obtained), SUM(total)
        FROM scores
        GROUP BY subject, chapter
        ORDER BY subject, chapter
    """)

    win = tk.Toplevel(root)
    win.title("Chapter-Wise Performance")
    win.geometry("700x420")

    columns = (
        "Subject", "Chapter", "Marks Obtained",
        "Total Marks", "Percentage", "Status"
    )

    tree = ttk.Treeview(
        win, columns=columns, show="headings"
    )

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=110, anchor="center")

    tree.pack(fill="both", expand=True, padx=10, pady=10)

    if not rows:
        ttk.Label(
            win,
            text="No test scores recorded yet. Record scores first."
        ).pack(pady=10)
        return

    for subject, chapter, obtained, total in rows:
        percentage = obtained / total * 100

        if percentage < 50:
            status = "Needs revision"
        elif percentage < 75:
            status = "Moderate"
        else:
            status = "Strong"

        tree.insert("", "end", values=(
            subject, chapter,
            f"{obtained:g}", f"{total:g}",
            f"{percentage:.1f}%", status
        ))

    def show_graph():
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror(
                "Matplotlib not installed",
                "Open Anaconda Prompt and run:\n"
                "conda install matplotlib\n"
                "Then restart Spyder."
            )
            return

        names = [f"{r[0]}: {r[1]}" for r in rows]
        percentages = [r[2] / r[3] * 100 for r in rows]

        plt.figure(figsize=(10, 5))
        bars = plt.bar(names, percentages)
        plt.axhline(50, linestyle="--", label="Revision threshold")
        plt.ylim(0, 100)
        plt.ylabel("Performance (%)")
        plt.title("Chapter-Wise Performance Analysis")
        plt.xticks(rotation=35, ha="right")
        plt.legend()

        for bar, value in zip(bars, percentages):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                value + 1, f"{value:.0f}%",
                ha="center"
            )

        plt.tight_layout()
        plt.show()

    ttk.Button(
        win, text="Show Performance Graph", command=show_graph
    ).pack(pady=(0, 12))


# -----------------------------------------
# MAIN APPLICATION WINDOW
# ----------------------------------------

root = tk.Tk()
root.title("Previous Question Paper Analyzer")
root.geometry("950x620")
root.minsize(800, 550)
root.configure(bg="#F3F6FB")

BG = "#F3F6FB"
NAVY = "#142D4E"
BLUE = "#2563EB"
WHITE = "#FFFFFF"
TEXT = "#24364B"
MUTED = "#64748B"

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "TButton",
    font=("Arial", 11),
    padding=10,
    background=BLUE,
    foreground=WHITE
)

style.map(
    "TButton",
    background=[("active", "#1D4ED8")]
)

style.configure(
    "TLabel",
    font=("Arial", 10),
    background=WHITE,
    foreground=TEXT
)

# Main layout
main_frame = tk.Frame(root, bg=BG)
main_frame.pack(fill="both", expand=True)

# Sidebar
sidebar = tk.Frame(main_frame, bg=NAVY, width=235)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

tk.Label(
    sidebar,
    text="QUESTION\nPAPER ANALYZER",
    font=("Arial", 16, "bold"),
    bg=NAVY,
    fg=WHITE,
    justify="left"
).pack(anchor="w", padx=14, pady=(35, 8))

tk.Label(
    sidebar,
    text="STUDENT WORKSPACE",
    font=("Arial", 9),
    bg=NAVY,
    fg="#B8CBE3"
).pack(anchor="w", padx=22, pady=(0, 35))

# Content area
content = tk.Frame(main_frame, bg=BG)
content.pack(side="left", fill="both", expand=True,
             padx=28, pady=25)

tk.Label(
    content,
    text="Dashboard",
    font=("Arial", 25, "bold"),
    bg=BG,
    fg=NAVY
).pack(anchor="w")

tk.Label(
    content,
    text="Prepare smarter. Track progress. Improve results.",
    font=("Arial", 11),
    bg=BG,
    fg=MUTED
).pack(anchor="w", pady=(5, 22))

# Summary cards
cards = tk.Frame(content, bg=BG)
cards.pack(fill="x", pady=(0, 22))

question_count = get_values(
    "SELECT COUNT(*) FROM questions"
)[0][0]

subject_count = len(get_subjects())

test_count = get_values(
    "SELECT COUNT(*) FROM scores"
)[0][0]

card_data = [
    ("TOTAL QUESTIONS", question_count),
    ("TOTAL SUBJECTS", subject_count),
    ("TESTS RECORDED", test_count)
]

for title, value in card_data:
    card = tk.Frame(
        cards,
        bg=WHITE,
        highlightbackground="#E2E8F0",
        highlightthickness=1
    )
    card.pack(side="left", fill="both",
              expand=True, padx=(0, 10))

    tk.Label(
        card,
        text=title,
        font=("Arial", 9, "bold"),
        bg=WHITE,
        fg=MUTED
    ).pack(anchor="w", padx=13, pady=(14, 5))

    tk.Label(
        card,
        text=str(value),
        font=("Arial", 23, "bold"),
        bg=WHITE,
        fg=BLUE
    ).pack(anchor="w", padx=13, pady=(0, 14))

# Feature buttons
tk.Label(
    content,
    text="Manage Your Studies",
    font=("Arial", 15, "bold"),
    bg=BG,
    fg=NAVY
).pack(anchor="w", pady=(0, 12))

button_frame = tk.Frame(content, bg=BG)
button_frame.pack(fill="both", expand=True)

buttons = [
    ("Add a Question", add_question),
    ("View Question Bank", view_questions),
    ("Generate Practice Paper", generate_paper),
    ("Record Test Score", record_score),
    ("Chapter-Wise Performance", analyze_performance)
]

for label, function in buttons:
    tk.Button(
        button_frame,
        text=label,
        command=function,
        font=("Arial", 11, "bold"),
        bg=WHITE,
        fg=TEXT,
        activebackground="#DBEAFE",
        activeforeground=NAVY,
        relief="flat",
        bd=0,
        anchor="w",
        padx=18,
        pady=12,
        cursor="hand2",
        highlightbackground="#E2E8F0",
        highlightthickness=1
    ).pack(fill="x", pady=5)

# Status
status_label = tk.Label(
    content,
    text="",
    font=("Arial", 10),
    bg=BG,
    fg=MUTED
)
status_label.pack(anchor="w", pady=(12, 0))

refresh_status()

def close_application():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", close_application)
root.mainloop()
