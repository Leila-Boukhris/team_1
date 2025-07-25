import tkinter as tk
from tkinter import ttk
import threading
import time
import random

class LoadingPage:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Loading Page")
        self.root.geometry("500x300")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        self.loading_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.title_label = tk.Label(self.loading_frame, text="Initialisation en cours...", fg="white", bg="#1e1e1e", font=("Helvetica", 16))
        self.title_label.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(self.loading_frame, orient=tk.HORIZONTAL, length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor="#333", background="#4caf50", bordercolor="#333", lightcolor="#4caf50", darkcolor="#4caf50")

        self.dynamic_label = tk.Label(self.loading_frame, text="", fg="#aaaaaa", bg="#1e1e1e", font=("Helvetica", 10))
        self.dynamic_label.pack(pady=5)

        self.loading_messages = [
            "Connexion au serveur...",
            "Chargement des modules...",
            "Synchronisation des données...",
            "Vérification de la configuration...",
            "Finalisation..."
        ]

        self.current_index = 0
        self.running = True

        self.start_animation()
        self.start_loading_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def start_animation(self):
        self.progress.start(10)
        self.update_dynamic_text()

    def update_dynamic_text(self):
        if not self.running:
            return
        message = self.loading_messages[self.current_index % len(self.loading_messages)]
        self.dynamic_label.config(text=message)
        self.current_index += 1
        self.root.after(1500, self.update_dynamic_text)

    def start_loading_thread(self):
        t = threading.Thread(target=self.simulate_loading, daemon=True)
        t.start()

    def simulate_loading(self):
        total_time = 8
        steps = 16
        for _ in range(steps):
            if not self.running:
                return
            time.sleep(total_time / steps)
        self.on_loading_complete()

    def on_loading_complete(self):
        self.running = False
        self.progress.stop()
        self.title_label.config(text="Chargement terminé.")
        self.dynamic_label.config(text="Lancement de l'application...")
        self.root.after(2000, self.root.destroy)

    def on_close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    LoadingPage()
import tkinter as tk
from tkinter import ttk
import threading
import time
import random

class LoadingPage:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Loading Page")
        self.root.geometry("500x300")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        self.loading_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.title_label = tk.Label(self.loading_frame, text="Initialisation en cours...", fg="white", bg="#1e1e1e", font=("Helvetica", 16))
        self.title_label.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(self.loading_frame, orient=tk.HORIZONTAL, length=300, mode="indeterminate")
        self.progress.pack(pady=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor="#333", background="#4caf50", bordercolor="#333", lightcolor="#4caf50", darkcolor="#4caf50")

        self.dynamic_label = tk.Label(self.loading_frame, text="", fg="#aaaaaa", bg="#1e1e1e", font=("Helvetica", 10))
        self.dynamic_label.pack(pady=5)

        self.loading_messages = [
            "Connexion au serveur...",
            "Chargement des modules...",
            "Synchronisation des données...",
            "Vérification de la configuration...",
            "Finalisation..."
        ]

        self.current_index = 0
        self.running = True

        self.start_animation()
        self.start_loading_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def start_animation(self):
        self.progress.start(10)
        self.update_dynamic_text()

    def update_dynamic_text(self):
        if not self.running:
            return
        message = self.loading_messages[self.current_index % len(self.loading_messages)]
        self.dynamic_label.config(text=message)
        self.current_index += 1
        self.root.after(1500, self.update_dynamic_text)

    def start_loading_thread(self):
        t = threading.Thread(target=self.simulate_loading, daemon=True)
        t.start()

    def simulate_loading(self):
        total_time = 8
        steps = 16
        for _ in range(steps):
            if not self.running:
                return
            time.sleep(total_time / steps)
        self.on_loading_complete()

    def on_loading_complete(self):
        self.running = False
        self.progress.stop()
        self.title_label.config(text="Chargement terminé.")
        self.dynamic_label.config(text="Lancement de l'application...")
        self.root.after(2000, self.root.destroy)

    def on_close(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    LoadingPage()
