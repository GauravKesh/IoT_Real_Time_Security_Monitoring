import tkinter as tk
import threading  # ← ADD THIS

CORRECT_PASSWORD = "123"
WAIT_TIMES = [0, 5, 10, 20, 30]


def authenticate_ui(on_fail_start=None, on_fail_end=None, on_wrong_password=None):
    result = {"success": False}
    attempts = {"count": 0}

    root = tk.Tk()
    root.title("🔐 Security Access")
    root.geometry("300x240")
    root.resizable(False, False)
    root.configure(bg="#1a1a1a")
    root.option_add("*Background", "#1a1a1a")
    root.option_add("*Foreground", "white")

    def clear():
        for w in root.winfo_children():
            w.destroy()

    def show_start_screen():
        clear()
        wait_idx  = min(attempts["count"], len(WAIT_TIMES) - 1)
        wait_secs = WAIT_TIMES[wait_idx]

        if attempts["count"] == 0:
            tk.Label(root, text="🔐 Security System", font=("Arial", 16, "bold")).pack(pady=20)
            tk.Label(root, text="Press Start to authenticate", font=("Arial", 12)).pack(pady=5)
            tk.Button(
                root, text="▶  Start", font=("Arial", 13),
                bg="#222", fg="white", padx=20, pady=8,
                command=show_password_screen
            ).pack(pady=20)

        else:
            # ← run in thread so Tkinter mainloop stays alive during join
            if on_fail_start:
                threading.Thread(target=on_fail_start, daemon=True).start()

            tk.Label(
                root, text=f"❌ Failed Attempt #{attempts['count']}",
                font=("Arial", 14, "bold"), fg="red"
            ).pack(pady=15)

            wait_label = tk.Label(root, text=f"⏳ Wait {wait_secs}s before retrying", font=("Arial", 12))
            wait_label.pack(pady=5)

            start_btn = tk.Button(
                root, text="▶  Start", font=("Arial", 13),
                bg="#555", fg="white", padx=20, pady=8, state=tk.DISABLED
            )
            start_btn.pack(pady=10)

            def on_start_clicked():
                if on_fail_end:
                    on_fail_end()
                show_password_screen()

            def countdown(remaining):
                if remaining > 0:
                    wait_label.config(text=f"⏳ Wait {remaining}s before retrying")
                    root.after(1000, countdown, remaining - 1)
                else:
                    wait_label.config(text="✅ You may try again")
                    start_btn.config(state=tk.NORMAL, bg="#222", command=on_start_clicked)

            countdown(wait_secs)

    def show_password_screen():
        clear()

        tk.Label(root, text="Enter Passkey", font=("Arial", 14)).pack(pady=15)

        entry = tk.Entry(root, show="*", font=("Arial", 14))
        entry.pack(pady=10)
        entry.focus()

        msg_label = tk.Label(root, text="", font=("Arial", 11), fg="red")
        msg_label.pack(pady=2)

        tk.Button(
            root, text="Submit", font=("Arial", 13),
            bg="#222", fg="white", padx=20, pady=6,
            command=lambda: check_password(entry, msg_label)
        ).pack(pady=10)

        root.bind("<Return>", lambda e: check_password(entry, msg_label))

        tk.Button(
            root, text="← Back", font=("Arial", 10),
            bg="#333", fg="white", command=show_start_screen
        ).pack(pady=2)

    def check_password(entry, msg_label):
        val = entry.get()

        if val == CORRECT_PASSWORD:
            result["success"] = True
            clear()
            tk.Label(root, text="✅ Access Granted", font=("Arial", 16, "bold"), fg="green").pack(pady=40)
            root.after(800, root.destroy)

        else:
            attempts["count"] += 1
            msg_label.config(text="❌ Wrong password")
            entry.delete(0, tk.END)

            if on_wrong_password:
                on_wrong_password(attempts["count"])

            root.after(200, show_start_screen)

    show_start_screen()
    root.mainloop()
    return result["success"]