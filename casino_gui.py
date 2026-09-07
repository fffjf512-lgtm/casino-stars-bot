import tkinter as tk
from tkinter import ttk, messagebox
import random
import json
import os
import time
import threading

DB_FILE = os.path.join(os.path.dirname(__file__), "users.json")

# Rocket game chances
CRASH_POINTS = [
    (1.0, 0.03),
    (1.1, 0.15),
    (1.2, 0.25),
    (1.5, 0.45),
    (1.8, 0.58),
    (2.0, 0.68),
    (2.5, 0.78),
    (3.0, 0.85),
    (5.0, 0.92),
    (10.0, 0.96),
    (20.0, 0.985),
    (50.0, 1.0),
]

COLORS = {
    "bg": "#1a1a2e",
    "bg2": "#16213e",
    "bg3": "#0f3460",
    "accent": "#e94560",
    "gold": "#f5c518",
    "green": "#00d26a",
    "red": "#ff4757",
    "text": "#ffffff",
    "text2": "#a0a0b0",
    "button": "#e94560",
    "button_hover": "#ff6b81",
}


def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_crash_point():
    roll = random.random()
    for multiplier, cumulative_prob in CRASH_POINTS:
        if roll <= cumulative_prob:
            return multiplier
    return CRASH_POINTS[-1][0]


class CasinoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Casino Stars")
        self.root.geometry("500x700")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        self.users = load_users()
        self.current_user = None
        self.current_frame = None

        self.show_login()

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

    def show_login(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="CASINO", font=("Arial", 40, "bold"),
                 fg=COLORS["gold"], bg=COLORS["bg"]).pack(pady=(40, 5))
        tk.Label(frame, text="STARS", font=("Arial", 20),
                 fg=COLORS["text2"], bg=COLORS["bg"]).pack(pady=(0, 40))

        tk.Label(frame, text="Имя игрока:", font=("Arial", 12),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(anchor="w")
        self.username_entry = tk.Entry(frame, font=("Arial", 14), bg=COLORS["bg2"],
                                        fg=COLORS["text"], insertbackground=COLORS["text"],
                                        relief="flat", bd=0)
        self.username_entry.pack(fill="x", ipady=8, pady=(5, 15))

        login_btn = tk.Button(frame, text="ИГРАТЬ", font=("Arial", 14, "bold"),
                               bg=COLORS["button"], fg=COLORS["text"],
                               activebackground=COLORS["button_hover"],
                               relief="flat", cursor="hand2", command=self.login)
        login_btn.pack(fill="x", ipady=10, pady=10)

        tk.Label(frame, text="Первый раз? Имя будет создано автоматически",
                 font=("Arial", 9), fg=COLORS["text2"], bg=COLORS["bg"]).pack(pady=20)

    def login(self):
        name = self.username_entry.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Введите имя!")
            return
        if name not in self.users:
            self.users[name] = {"balance": 100, "total_won": 0, "total_lost": 0, "games": 0}
            save_users(self.users)
        self.current_user = name
        self.show_main()

    def show_main(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text=f"Привет, {self.current_user}!",
                 font=("Arial", 18, "bold"), fg=COLORS["text"], bg=COLORS["bg"]).pack(pady=(20, 5))

        user = self.users[self.current_user]
        self.balance_label = tk.Label(frame, text=f"{user['balance']} \u2b50",
                                       font=("Arial", 36, "bold"), fg=COLORS["gold"], bg=COLORS["bg"])
        self.balance_label.pack(pady=10)

        tk.Label(frame, text="Твой баланс", font=("Arial", 11),
                 fg=COLORS["text2"], bg=COLORS["bg"]).pack()

        buttons_frame = tk.Frame(frame, bg=COLORS["bg"])
        buttons_frame.pack(fill="x", pady=30)

        self.make_button(buttons_frame, "\U0001f680  РАКЕТА", COLORS["accent"], self.show_rocket).pack(fill="x", ipady=12, pady=5)
        self.make_button(buttons_frame, "\u2b50  ДЕПОЗИТ", COLORS["green"], self.show_deposit).pack(fill="x", ipady=12, pady=5)
        self.make_button(buttons_frame, "\U0001f4b8  ВЫВОД", "#3498db", self.show_withdraw).pack(fill="x", ipady=12, pady=5)
        self.make_button(buttons_frame, "\U0001f4ca  СТАТИСТИКА", COLORS["bg3"], self.show_stats).pack(fill="x", ipady=12, pady=5)

        tk.Button(frame, text="Выйти", font=("Arial", 10), fg=COLORS["text2"],
                  bg=COLORS["bg"], activebackground=COLORS["bg"],
                  relief="flat", cursor="hand2", command=self.show_login).pack(side="bottom", pady=10)

    def make_button(self, parent, text, color, command):
        btn = tk.Button(parent, text=text, font=("Arial", 14, "bold"),
                        bg=color, fg=COLORS["text"], activebackground=color,
                        relief="flat", cursor="hand2", command=command)
        return btn

    def update_balance_label(self):
        if self.balance_label:
            user = self.users[self.current_user]
            self.balance_label.config(text=f"{user['balance']} \u2b50")

    def show_deposit(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="\u2b50 ДЕПОЗИТ", font=("Arial", 24, "bold"),
                 fg=COLORS["green"], bg=COLORS["bg"]).pack(pady=(30, 10))

        tk.Label(frame, text="Сколько звёзд добавить?", font=("Arial", 12),
                 fg=COLORS["text2"], bg=COLORS["bg"]).pack()

        amounts_frame = tk.Frame(frame, bg=COLORS["bg"])
        amounts_frame.pack(fill="x", pady=20)

        for amount in [10, 25, 50, 100, 250, 500]:
            btn = tk.Button(amounts_frame, text=f"{amount} \u2b50", font=("Arial", 12, "bold"),
                            bg=COLORS["bg2"], fg=COLORS["gold"], activebackground=COLORS["bg3"],
                            relief="flat", cursor="hand2",
                            command=lambda a=amount: self.do_deposit(a))
            btn.pack(side="left", expand=True, fill="both", padx=3, ipady=8)

        custom_frame = tk.Frame(frame, bg=COLORS["bg"])
        custom_frame.pack(fill="x", pady=10)
        tk.Label(custom_frame, text="Своя сумма:", font=("Arial", 11),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(side="left")
        self.dep_entry = tk.Entry(custom_frame, font=("Arial", 14), bg=COLORS["bg2"],
                                   fg=COLORS["text"], insertbackground=COLORS["text"],
                                   relief="flat", width=8)
        self.dep_entry.pack(side="left", padx=10, ipady=5)
        tk.Button(custom_frame, text="OK", font=("Arial", 12, "bold"),
                  bg=COLORS["green"], fg=COLORS["text"], relief="flat",
                  cursor="hand2", command=self.do_custom_deposit).pack(side="left", ipady=2)

        self.make_button(frame, "Назад", COLORS["bg3"], self.show_main).pack(fill="x", ipady=10, side="bottom", pady=10)

    def do_deposit(self, amount):
        self.users[self.current_user]["balance"] += amount
        save_users(self.users)
        messagebox.showinfo("Успешно", f"+{amount} \u2b50 добавлено на баланс!")
        self.show_main()

    def do_custom_deposit(self):
        try:
            amount = int(self.dep_entry.get())
            if amount <= 0:
                raise ValueError
            self.do_deposit(amount)
        except ValueError:
            messagebox.showwarning("Ошибка", "Введите положительное число!")

    def show_withdraw(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        user = self.users[self.current_user]
        tk.Label(frame, text="\U0001f4b8 ВЫВОД", font=("Arial", 24, "bold"),
                 fg="#3498db", bg=COLORS["bg"]).pack(pady=(30, 10))

        tk.Label(frame, text=f"Баланс: {user['balance']} \u2b50", font=("Arial", 14),
                 fg=COLORS["gold"], bg=COLORS["bg"]).pack()

        tk.Label(frame, text="Сколько звёзд вывести?", font=("Arial", 12),
                 fg=COLORS["text2"], bg=COLORS["bg"]).pack(pady=10)

        self.wd_entry = tk.Entry(frame, font=("Arial", 14), bg=COLORS["bg2"],
                                  fg=COLORS["text"], insertbackground=COLORS["text"],
                                  relief="flat", justify="center")
        self.wd_entry.pack(ipady=8, pady=10)

        def do_withdraw():
            try:
                amount = int(self.wd_entry.get())
                if amount <= 0:
                    raise ValueError
                if amount > user['balance']:
                    messagebox.showwarning("Ошибка", "Недостаточно средств!")
                    return
                self.users[self.current_user]["balance"] -= amount
                save_users(self.users)
                messagebox.showinfo("Успешно", f"{amount} \u2b50 выведено!")
                self.show_main()
            except ValueError:
                messagebox.showwarning("Ошибка", "Введите число!")

        self.make_button(frame, "Вывести", "#3498db", do_withdraw).pack(fill="x", ipady=10, pady=10)
        self.make_button(frame, "Назад", COLORS["bg3"], self.show_main).pack(fill="x", ipady=10, side="bottom", pady=10)

    def show_stats(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        user = self.users[self.current_user]
        profit = user['total_won'] - user['total_lost']

        tk.Label(frame, text="\U0001f4ca СТАТИСТИКА", font=("Arial", 24, "bold"),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(pady=(30, 20))

        stats_data = [
            ("Баланс", f"{user['balance']} \u2b50", COLORS["gold"]),
            ("Игр сыграно", str(user['games']), COLORS["text"]),
            ("Выиграно", f"{user['total_won']} \u2b50", COLORS["green"]),
            ("Проиграно", f"{user['total_lost']} \u2b50", COLORS["red"]),
            ("Профит", f"{'+' if profit >= 0 else ''}{profit} \u2b50",
             COLORS["green"] if profit >= 0 else COLORS["red"]),
        ]

        for label, value, color in stats_data:
            row = tk.Frame(frame, bg=COLORS["bg"])
            row.pack(fill="x", pady=8)
            tk.Label(row, text=label, font=("Arial", 13), fg=COLORS["text2"],
                     bg=COLORS["bg"]).pack(side="left")
            tk.Label(row, text=value, font=("Arial", 13, "bold"), fg=color,
                     bg=COLORS["bg"]).pack(side="right")

        self.make_button(frame, "Назад", COLORS["bg3"], self.show_main).pack(fill="x", ipady=10, side="bottom", pady=10)

    def show_rocket(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.current_frame = frame
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        user = self.users[self.current_user]

        tk.Label(frame, text="\U0001f680 РАКЕТА", font=("Arial", 24, "bold"),
                 fg=COLORS["accent"], bg=COLORS["bg"]).pack(pady=(10, 5))

        tk.Label(frame, text=f"Баланс: {user['balance']} \u2b50", font=("Arial", 12),
                 fg=COLORS["gold"], bg=COLORS["bg"]).pack()

        self.rocket_canvas = tk.Canvas(frame, bg="#0d1117", height=300,
                                        highlightthickness=0)
        self.rocket_canvas.pack(fill="x", pady=15)

        self.mult_label = tk.Label(frame, text="x1.00", font=("Arial", 32, "bold"),
                                    fg=COLORS["text"], bg=COLORS["bg"])
        self.mult_label.pack(pady=5)

        self.win_label = tk.Label(frame, text="", font=("Arial", 14),
                                   fg=COLORS["green"], bg=COLORS["bg"])
        self.win_label.pack()

        bet_frame = tk.Frame(frame, bg=COLORS["bg"])
        bet_frame.pack(fill="x", pady=10)

        tk.Label(bet_frame, text="Ставка:", font=("Arial", 12),
                 fg=COLORS["text"], bg=COLORS["bg"]).pack(side="left")
        self.bet_var = tk.StringVar(value="10")
        bet_spin = tk.Spinbox(bet_frame, from_=1, to=min(1000, user['balance']),
                               textvariable=self.bet_var, font=("Arial", 14),
                               bg=COLORS["bg2"], fg=COLORS["text"],
                               insertbackground=COLORS["text"],
                               relief="flat", width=6, justify="center")
        bet_spin.pack(side="left", padx=10, ipady=3)

        btn_frame = tk.Frame(frame, bg=COLORS["bg"])
        btn_frame.pack(fill="x", pady=5)

        self.start_btn = tk.Button(btn_frame, text="\u25b6 ЗАПУСТИТЬ", font=("Arial", 14, "bold"),
                                    bg=COLORS["accent"], fg=COLORS["text"],
                                    activebackground=COLORS["button_hover"],
                                    relief="flat", cursor="hand2",
                                    command=self.start_rocket)
        self.start_btn.pack(fill="x", ipady=10)

        self.cashout_btn = tk.Button(btn_frame, text="\U0001f4b0 ЗАБРАТЬ", font=("Arial", 14, "bold"),
                                      bg=COLORS["green"], fg=COLORS["text"],
                                      activebackground="#00b85d",
                                      relief="flat", cursor="hand2",
                                      state="disabled", command=self.cashout_rocket)
        self.cashout_btn.pack(fill="x", ipady=10, pady=5)

        self.make_button(frame, "Назад", COLORS["bg3"], self.show_main).pack(fill="x", ipady=8, side="bottom", pady=5)

        self.rocket_running = False
        self.current_multiplier = 1.0
        self.crash_point = 0
        self.bet_amount = 0

    def draw_rocket(self, mult):
        c = self.rocket_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()

        c.create_rectangle(0, 0, w, h, fill="#0d1117", outline="")

        grid_color = "#1a2332"
        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=grid_color)
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=grid_color)

        progress = min((mult - 1.0) / 10.0, 1.0)
        rocket_x = 40 + progress * (w - 80)
        rocket_y = h - 40 - progress * (h - 100)

        flame_colors = [COLORS["gold"], COLORS["accent"], "#ff6b35"]
        for i, color in enumerate(flame_colors):
            flame_y = rocket_y + 15 + i * 8
            flame_size = 6 - i * 1.5
            c.create_oval(rocket_x - flame_size, flame_y,
                          rocket_x + flame_size, flame_y + flame_size * 2,
                          fill=color, outline="")

        c.create_polygon(rocket_x, rocket_y - 20,
                         rocket_x - 8, rocket_y + 15,
                         rocket_x + 8, rocket_y + 15,
                         fill=COLORS["text"], outline=COLORS["accent"], width=2)

        c.create_oval(rocket_x - 3, rocket_y - 8, rocket_x + 3, rocket_y - 2,
                       fill="#3498db", outline="")

        stars = [(random.randint(5, w - 5), random.randint(5, h - 5)) for _ in range(15)]
        for sx, sy in stars:
            brightness = random.randint(100, 255)
            c.create_oval(sx, sy, sx + 1, sy + 1, fill=f"#{brightness:02x}{brightness:02x}{brightness:02x}", outline="")

        trail_points = []
        for i in range(5):
            tx = rocket_x - i * 3 + random.randint(-2, 2)
            ty = rocket_y + 15 + i * 12
            trail_points.extend([tx, ty])
        if len(trail_points) >= 4:
            c.create_line(trail_points, fill=COLORS["gold"], width=2, smooth=True)

    def start_rocket(self):
        try:
            bet = int(self.bet_var.get())
        except ValueError:
            messagebox.showwarning("Ошибка", "Введите число!")
            return

        user = self.users[self.current_user]
        if bet > user['balance']:
            messagebox.showwarning("Ошибка", "Недостаточно средств!")
            return
        if bet <= 0:
            messagebox.showwarning("Ошибка", "Ставка должна быть > 0!")
            return

        self.bet_amount = bet
        self.users[self.current_user]["balance"] -= bet
        save_users(self.users)
        self.update_balance_label()

        self.crash_point = get_crash_point()
        self.current_multiplier = 1.0
        self.rocket_running = True

        self.start_btn.config(state="disabled")
        self.cashout_btn.config(state="normal")
        self.draw_rocket(1.0)
        self.fly_rocket()

    def fly_rocket(self):
        if not self.rocket_running:
            return

        self.current_multiplier = round(self.current_multiplier + random.uniform(0.05, 0.18), 2)

        if self.current_multiplier >= self.crash_point:
            self.current_multiplier = self.crash_point
            self.rocket_running = False
            self.rocket_crash()
            return

        win = int(self.bet_amount * self.current_multiplier)
        self.mult_label.config(text=f"x{self.current_multiplier:.2f}")
        self.win_label.config(text=f"Выигрыш: {win} \u2b50")
        self.draw_rocket(self.current_multiplier)

        self.root.after(400, self.fly_rocket)

    def cashout_rocket(self):
        if not self.rocket_running:
            return

        self.rocket_running = False
        payout = int(self.bet_amount * self.current_multiplier)
        profit = payout - self.bet_amount

        self.users[self.current_user]["balance"] += payout
        self.users[self.current_user]["total_won"] += payout
        self.users[self.current_user]["games"] += 1
        save_users(self.users)

        self.cashout_btn.config(state="disabled")
        self.mult_label.config(text=f"ЗАБРАЛ x{self.current_multiplier:.2f}", fg=COLORS["green"])
        self.win_label.config(text=f"+{profit} \u2b50", fg=COLORS["green"])

        messagebox.showinfo("Выигрыш!", f"Вы забрали {payout} \u2b50!\nПрофит: +{profit} \u2b50")
        self.show_main()

    def rocket_crash(self):
        self.users[self.current_user]["total_lost"] += self.bet_amount
        self.users[self.current_user]["games"] += 1
        save_users(self.users)

        self.cashout_btn.config(state="disabled")
        self.mult_label.config(text="ВЗОРВАЛСЯ!", fg=COLORS["red"])
        self.win_label.config(text=f"-{self.bet_amount} \u2b50", fg=COLORS["red"])

        self.draw_rocket(self.crash_point)
        w = self.rocket_canvas.winfo_width()
        h = self.rocket_canvas.winfo_height()
        self.rocket_canvas.create_text(w // 2, h // 2, text="BOOM!", font=("Arial", 28, "bold"),
                                        fill=COLORS["red"])

        self.root.after(1500, self.show_main)


if __name__ == "__main__":
    root = tk.Tk()
    app = CasinoApp(root)
    root.mainloop()
