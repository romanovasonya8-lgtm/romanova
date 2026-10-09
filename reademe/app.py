import os
import random
import tkinter as tk
from tkinter import ttk, messagebox

from models import *

CURRENT_USER = None
CURRENT_EDIT = None
ENTRY_LOGIN = None

BG = "#dbeafe"
FIELD_BG = "#ffffff"
FIELD_FG = "#1e293b"

FONT_TITLE = ("Georgia", 20, "bold")
FONT_LABEL = ("Calibri", 13)
FONT_BUTTON = ("Verdana", 12, "bold")
FONT_ITALIC = ("Calibri", 13, "italic")
FONT_TITLE_ITALIC = ("Georgia", 20, "bold italic")

WINDOW_W = 720
WINDOW_H = 860

root = tk.Tk()
root.title("Учебное приложение")

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
WINDOW_W = min(WINDOW_W, screen_w - 40)
WINDOW_H = min(WINDOW_H, screen_h - 80)
pos_x = (screen_w - WINDOW_W) // 2
pos_y = (screen_h - WINDOW_H) // 2
root.geometry(f"{WINDOW_W}x{WINDOW_H}+{pos_x}+{pos_y}")
root.configure(bg=BG)

container = tk.Frame(root, bg=BG)
container.pack(fill="both", expand=True, padx=20, pady=20)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTCHA_DIR = os.path.join(BASE_DIR, "captcha")
CORRECT_ORDER = [1, 2, 3, 4]
PIECE_SIZE = 90

captcha_images = {}
captcha_empty = None
captcha_host = None
captcha_slots = []
captcha_piece_widgets = {}
captcha_placed = []
captcha_shuffled = []
captcha_passed = False
captcha_fails = 0

drag_piece = None
drag_window = None


def _piece_color(gx, gy):
    r = 200 + int(55 * gx / 180)
    g = 220 + int(35 * gy / 180)
    b = 240
    cx, cy = 90, 90
    dist = (gx - cx) ** 2 + (gy - cy) ** 2
    if dist < 70 ** 2:
        r, g, b = 30, 95, 208
    elif dist < 80 ** 2:
        r, g, b = 255, 255, 255
    if abs(gx - gy) < 4 or abs(gx + gy - 180) < 4:
        r, g, b = 180, 35, 24
    return f"#{r:02x}{g:02x}{b:02x}"


def _generate_captcha_images():
    pieces = {}
    for piece in (1, 2, 3, 4):
        row = (piece - 1) // 2
        col = (piece - 1) % 2
        img = tk.PhotoImage(width=PIECE_SIZE, height=PIECE_SIZE)
        for y in range(PIECE_SIZE):
            for x in range(PIECE_SIZE):
                gx = col * PIECE_SIZE + x
                gy = row * PIECE_SIZE + y
                img.put(_piece_color(gx, gy), (x, y))
        pieces[piece] = img
    return pieces


def load_captcha_images():
    global captcha_images, captcha_empty
    captcha_images = {}
    try:
        for piece in (1, 2, 3, 4):
            path = os.path.join(CAPTCHA_DIR, f"piece_{piece}.png")
            img = tk.PhotoImage(file=path)
            if img.width() > PIECE_SIZE or img.height() > PIECE_SIZE:
                factor = max(1, min(img.width() // PIECE_SIZE,
                                    img.height() // PIECE_SIZE))
                img = img.subsample(factor)
            captcha_images[piece] = img
    except Exception:
        captcha_images = _generate_captcha_images()

    captcha_empty = tk.PhotoImage(width=PIECE_SIZE, height=PIECE_SIZE)
    captcha_empty.put(FIELD_BG, to=(0, 0, PIECE_SIZE, PIECE_SIZE))


def start_drag(event, piece):
    global drag_piece, drag_window
    if captcha_passed or len(captcha_placed) >= 4:
        return
    if piece in captcha_placed:
        return

    drag_piece = piece

    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    tk.Label(win, image=captcha_images[piece], bd=0).pack()
    win.geometry(
        f"+{event.x_root - PIECE_SIZE // 2}+{event.y_root - PIECE_SIZE // 2}"
    )
    drag_window = win

    root.bind("<B1-Motion>", do_drag)
    root.bind("<ButtonRelease-1>", end_drag)


def do_drag(event):
    if drag_window is None:
        return
    drag_window.geometry(
        f"+{event.x_root - PIECE_SIZE // 2}+{event.y_root - PIECE_SIZE // 2}"
    )


def end_drag(event):
    global drag_piece, drag_window
    if drag_piece is None:
        return

    piece = drag_piece
    target_slot = None

    for index, slot in enumerate(captcha_slots):
        sx = slot.winfo_rootx()
        sy = slot.winfo_rooty()
        sw = slot.winfo_width()
        sh = slot.winfo_height()
        if sx <= event.x_root <= sx + sw and sy <= event.y_root <= sy + sh:
            target_slot = index
            break

    if drag_window is not None:
        drag_window.destroy()
    drag_window = None
    drag_piece = None

    root.unbind("<B1-Motion>")
    root.unbind("<ButtonRelease-1>")

    if target_slot is None or target_slot != len(captcha_placed):
        return

    captcha_placed.append(piece)
    captcha_slots[target_slot].configure(image=captcha_images[piece])

    if len(captcha_placed) == 4:
        check_captcha()


def build_captcha(host):
    global captcha_slots, captcha_piece_widgets, captcha_placed, captcha_shuffled

    for w in host.winfo_children():
        w.destroy()

    captcha_slots = []
    captcha_piece_widgets = {}
    captcha_placed = []
    captcha_shuffled = CORRECT_ORDER[:]
    random.shuffle(captcha_shuffled)
    while captcha_shuffled == CORRECT_ORDER:
        random.shuffle(captcha_shuffled)

    tk.Label(
        host,
        text="Соберите картинку: перетаскивайте фрагменты в клетки по порядку",
        bg=BG, fg=FIELD_FG, font=FONT_ITALIC, anchor="w",
    ).pack(fill="x")

    board = tk.Frame(host, bg=BG)
    board.pack(pady=(6, 6))
    for index in range(4):
        slot = tk.Label(board, image=captcha_empty,
                        bg=FIELD_BG, relief="solid", borderwidth=1)
        slot.grid(row=index // 2, column=index % 2)
        captcha_slots.append(slot)

    pieces = tk.Frame(host, bg=BG)
    pieces.pack(pady=(0, 6))
    for piece in captcha_shuffled:
        lbl = tk.Label(pieces, image=captcha_images[piece],
                       relief="raised", borderwidth=2, cursor="hand2")
        lbl.pack(side="left", padx=3)
        lbl.bind("<ButtonPress-1>", lambda e, p=piece: start_drag(e, p))
        captcha_piece_widgets[piece] = lbl

    make_button("Сбросить капчу", new_captcha_round,
                parent=host).pack(ipadx=16, ipady=3)


def new_captcha_round():
    global captcha_passed
    captcha_passed = False
    build_captcha(captcha_host)


def check_captcha():
    global captcha_passed, captcha_fails
    login = ENTRY_LOGIN.get().strip()

    if captcha_placed == CORRECT_ORDER:
        captcha_passed = True
        messagebox.showinfo("Капча",
                            "Пазл собран верно. Теперь можно нажимать «Войти».")
        return

    if login_exists(login):
        became_locked = register_fail(login)
        if became_locked:
            messagebox.showerror("Блокировка",
                                 "Вы заблокированы. Обратитесь к администратору")
        else:
            messagebox.showerror("Капча",
                                 "Пазл собран неверно. Попробуйте собрать ещё раз, "
                                 "ориентируясь на продолжение рисунка.")
    else:
        captcha_fails = captcha_fails + 1
        if captcha_fails >= 3:
            messagebox.showerror("Блокировка",
                                 "Третья неверная сборка капчи подряд. "
                                 "При входе учётная запись будет заблокирована.")
        else:
            messagebox.showerror("Капча",
                                 "Пазл собран неверно. Попробуйте собрать ещё раз, "
                                 "ориентируясь на продолжение рисунка.")
    new_captcha_round()


def clear_screen():
    for w in container.winfo_children():
        w.destroy()


def make_title(text, font=None):
    return tk.Label(container, text=text, bg=BG, fg=FIELD_FG,
                    font=font if font is not None else FONT_TITLE)


def make_label(text):
    return tk.Label(container, text=text, bg=BG, fg=FIELD_FG,
                    font=FONT_LABEL, anchor="w")


def make_entry(password=False):
    entry = tk.Entry(container, font=FONT_BUTTON, bg=FIELD_BG, fg=FIELD_FG,
                     insertbackground=FIELD_FG, relief="solid", borderwidth=1)
    if password:
        entry.configure(show="*")
    return entry


def make_button(text, command, parent=None):
    host = container if parent is None else parent
    return tk.Button(host, text=text, command=command, font=FONT_BUTTON)


def toggle_password_visibility(entry_pass, var):
    entry_pass.configure(show="" if var.get() else "*")


def try_login(login, password):
    global CURRENT_USER, captcha_fails
    login = login.strip()
    password = password.strip()

    if not login or not password:
        messagebox.showwarning("Внимание", "Заполните логин и пароль.")
        return

    if captcha_fails > 0:
        if login_exists(login):
            for _ in range(captcha_fails):
                register_fail(login)
            captcha_fails = 0

    if not captcha_passed:
        messagebox.showwarning("Капча",
                               "Сначала соберите капчу, затем нажимайте «Войти».")
        return

    user = find_user(login, password)
    if user is None:
        became_locked = register_fail(login)
        if became_locked:
            messagebox.showerror("Блокировка",
                                 "Вы заблокированы. Обратитесь к администратору")
        else:
            messagebox.showerror(
                "Ошибка входа",
                "Вы ввели неверный логин или пароль. "
                "Пожалуйста проверьте ещё раз введенные данные")
        return

    if user["locked"]:
        messagebox.showerror("Блокировка",
                             "Вы заблокированы. Обратитесь к администратору")
        return

    reset_attempts(login)
    CURRENT_USER = user
    messagebox.showinfo("Авторизация", "Вы успешно авторизовались")
    new_captcha_round()

    if user["role"] == "Администратор":
        open_admin()
    else:
        open_user()


def open_login():
    global ENTRY_LOGIN, captcha_host
    clear_screen()
    make_title("Вход в систему", font=FONT_TITLE_ITALIC).pack(pady=(0, 10))

    make_label("Логин").pack(fill="x")
    ENTRY_LOGIN = make_entry()
    ENTRY_LOGIN.pack(fill="x", pady=(0, 8))

    make_label("Пароль").pack(fill="x")
    entry_pass = make_entry(password=True)
    entry_pass.pack(fill="x", pady=(0, 4))

    show_var = tk.BooleanVar(value=False)
    tk.Checkbutton(container, text="Показать пароль", variable=show_var,
                   command=lambda: toggle_password_visibility(entry_pass, show_var),
                   bg=BG, fg=FIELD_FG, activebackground=BG,
                   activeforeground=FIELD_FG, selectcolor=FIELD_BG,
                   font=FONT_LABEL, anchor="w").pack(fill="x", pady=(0, 10))

    captcha_host = tk.Frame(container, bg=BG)
    captcha_host.pack(fill="x", pady=(0, 10))
    build_captcha(captcha_host)

    make_button("Войти",
                lambda: try_login(ENTRY_LOGIN.get(), entry_pass.get())
                ).pack(fill="x", ipady=6)


def open_user():
    clear_screen()
    make_title("Рабочее место пользователя").pack(pady=(0, 10))
    make_label("Вы вошли как: " + CURRENT_USER["login"]).pack(fill="x", pady=(0, 6))
    make_label("Роль: " + CURRENT_USER["role"]).pack(fill="x", pady=(0, 20))
    make_button("Выйти", open_login).pack(ipadx=24, ipady=4)


def open_edit_user(login):
    global CURRENT_EDIT
    user = user_by_login(login)
    if user is None:
        messagebox.showwarning("Внимание", "Сначала выберите строку в таблице.")
        return

    CURRENT_EDIT = login
    clear_screen()
    make_title("Изменение пользователя").pack(pady=(0, 10))
    make_label("Логин: " + login).pack(fill="x", pady=(0, 10))

    make_label("ФИО").pack(fill="x")
    e_name = make_entry()
    e_name.insert(0, user["full_name"])
    e_name.pack(fill="x", pady=(0, 8))

    make_label("Пароль").pack(fill="x")
    e_pass = make_entry()
    e_pass.insert(0, user["password"])
    e_pass.pack(fill="x", pady=(0, 8))

    make_label("Роль").pack(fill="x")
    combo_role = ttk.Combobox(container,
                              values=["Пользователь", "Администратор"],
                              state="readonly", font=FONT_BUTTON)
    combo_role.set(user["role"])
    combo_role.pack(fill="x", pady=(0, 10))

    lock_text = "Заблокирован: да" if user["locked"] else "Заблокирован: нет"
    lock_label = make_label(lock_text)
    lock_label.pack(fill="x", pady=(0, 10))

    def refresh_lock():
        current = user_by_login(CURRENT_EDIT)
        lock_label.configure(
            text="Заблокирован: да" if current["locked"]
            else "Заблокирован: нет")

    def do_unlock():
        unlock_user(CURRENT_EDIT)
        refresh_lock()
        messagebox.showinfo("Готово",
                            "Пользователь " + CURRENT_EDIT + " разблокирован.")

    def do_save():
        name = e_name.get().strip()
        password = e_pass.get().strip()
        if not name or not password:
            messagebox.showwarning("Внимание",
                                   "ФИО и пароль не могут быть пустыми.")
            return
        update_user(CURRENT_EDIT, password, combo_role.get(), name)
        messagebox.showinfo("Готово", "Данные пользователя сохранены.")
        open_admin()

    def do_delete():
        if CURRENT_EDIT == "admin":
            messagebox.showerror("Ошибка",
                                 "Учётную запись администратора удалять нельзя.")
            return
        if messagebox.askyesno("Удаление",
                               "Удалить пользователя " + CURRENT_EDIT + "?"):
            delete_user(CURRENT_EDIT)
            messagebox.showinfo("Готово", "Пользователь удалён.")
            open_admin()

    row = tk.Frame(container, bg=BG)
    row.pack(fill="x")
    make_button("Сохранить", do_save, parent=row).pack(side="left", padx=(0, 6))
    make_button("Разблокировать", do_unlock, parent=row).pack(side="left", padx=(0, 6))
    make_button("Удалить", do_delete, parent=row).pack(side="left", padx=(0, 6))
    make_button("Отмена", open_admin, parent=row).pack(side="right")


def open_admin():
    clear_screen()
    if CURRENT_USER is None:
        open_login()
        return

    make_title("Панель администратора").pack(pady=(0, 5))
    make_label("Вы вошли как: " + CURRENT_USER["login"]).pack(fill="x", pady=(0, 10))

    tree = ttk.Treeview(container,
                        columns=("login", "full_name", "role", "locked"),
                        show="headings", height=8)
    tree.heading("login", text="Логин")
    tree.heading("full_name", text="ФИО")
    tree.heading("role", text="Роль")
    tree.heading("locked", text="Заблокирован")
    tree.column("login", width=120, anchor="w")
    tree.column("full_name", width=180, anchor="w")
    tree.column("role", width=130, anchor="w")
    tree.column("locked", width=110, anchor="center")

    for u in all_users():
        tree.insert("", "end", values=(u["login"], u["full_name"], u["role"],
                                       "да" if u["locked"] else "нет"))
    tree.pack(fill="both", expand=True, pady=(0, 10))

    def edit_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Внимание",
                                   "Сначала выберите строку в таблице.")
            return
        open_edit_user(tree.item(selected[0])["values"][0])

    row = tk.Frame(container, bg=BG)
    row.pack(fill="x")
    make_button("Добавить", open_add_user, parent=row).pack(side="left", padx=(0, 6))
    make_button("Изменить", edit_selected, parent=row).pack(side="left", padx=(0, 6))
    make_button("Выйти", open_login, parent=row).pack(side="right")


def save_user(login, password, role, full_name):
    login = login.strip()
    password = password.strip()
    if not login or not password or not full_name.strip():
        messagebox.showwarning("Внимание",
                               "Логин, пароль и ФИО не могут быть пустыми.")
        return
    if login_exists(login):
        messagebox.showerror("Ошибка", "Такой логин уже существует.")
        return
    add_user(login, password, role, full_name.strip())
    messagebox.showinfo("Готово", "Пользователь " + login + " добавлен.")
    open_admin()


def open_add_user():
    clear_screen()
    make_title("Новый пользователь").pack(pady=(0, 15))

    make_label("Логин").pack(fill="x")
    e_login = make_entry()
    e_login.pack(fill="x", pady=(0, 10))

    make_label("ФИО").pack(fill="x")
    e_name = make_entry()
    e_name.pack(fill="x", pady=(0, 10))

    make_label("Пароль").pack(fill="x")
    e_pass = make_entry()
    e_pass.pack(fill="x", pady=(0, 10))

    make_label("Роль").pack(fill="x")
    combo_role = ttk.Combobox(container,
                              values=["Пользователь", "Администратор"],
                              state="readonly", font=FONT_BUTTON)
    combo_role.current(0)
    combo_role.pack(fill="x", pady=(0, 15))

    make_button("Сохранить",
                lambda: save_user(e_login.get(), e_pass.get(),
                                  combo_role.get(), e_name.get())
                ).pack(fill="x", ipady=6)

    make_button("Отмена", open_admin).pack(fill="x", pady=(8, 0), ipady=4)


if __name__ == "__main__":
    load_captcha_images()
    open_login()
    root.mainloop()
