from dotenv import load_dotenv
import os
import threading
import time
from encrypt_decrypt import encrypt_file, decrypt_file
import pyotp
import sqlite3
from tkinter import messagebox, Tk, Toplevel  # ✅ Toplevel from tkinter
from ttkbootstrap import Style
from ttkbootstrap import ttk  # ✅ All widgets imported from here

# Load MFA secret from .env
load_dotenv()
secret = os.getenv("MFA_SECRET")


def verify_mfa(code, secret):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def login():
    username = entry_username.get()
    password = entry_password.get()
    mfa_code = entry_mfa.get()

    if username == "Vilgefortz" and password == "Gwentify":
        if verify_mfa(mfa_code, secret):
            messagebox.showinfo("Success", "Login Successful")
            decrypt_database()
            threading.Timer(120, encrypt_database).start()
            show_database_content()
        else:
            messagebox.showerror("Error", "Invalid MFA Code")
    else:
        messagebox.showerror("Error", "Invalid Username or Password")


def decrypt_database():
    with open("private.pem", "rb") as f:
        private_key = f.read()
    decrypt_file("parking_data.db.enc", private_key, "parking_data.db")
    print("Database Decrypted. Access granted for 120 seconds.")


def encrypt_database():
    with open("public.pem", "rb") as f:
        public_key = f.read()
    encrypt_file("parking_data.db", public_key)
    print("Database Encrypted. Access revoked.")


def show_database_content():
    data_window = Toplevel(app)  # ✅ Correctly use tkinter.Toplevel
    data_window.title("Parking Data")
    data_window.geometry("800x500")

    conn = sqlite3.connect('parking_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM parking_data")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    tree = ttk.Treeview(data_window, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")

    for row in rows:
        tree.insert("", "end", values=row)

    tree.pack(fill="both", expand=True, pady=10, padx=10)

    scrollbar = ttk.Scrollbar(data_window, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    ttk.Button(data_window, text="Exit", command=data_window.destroy).pack(pady=10)
    conn.close()


# GUI Setup
app = Tk()
style = Style(theme="cosmo")
style.master = app

app.title("Secure Database Login")
app.geometry("400x300")
app.resizable(False, False)

frame = ttk.Frame(app, padding=20)
frame.pack(fill="both", expand=True)

ttk.Label(frame, text="Username:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
entry_username = ttk.Entry(frame)
entry_username.pack(fill="x", pady=5)

ttk.Label(frame, text="Password:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
entry_password = ttk.Entry(frame, show="*")
entry_password.pack(fill="x", pady=5)

ttk.Label(frame, text="MFA Code:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
entry_mfa = ttk.Entry(frame)
entry_mfa.pack(fill="x", pady=5)

ttk.Button(frame, text="Login", command=login).pack(pady=10)

app.mainloop()

