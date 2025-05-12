import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
from encrypt_decrypt import encrypt_file, decrypt_file
import pyotp
import sqlite3

# Replace with the MFA generated secret key 
secret = "USA5VT6QKR3OAEQBY6BEMOV7XLE5T7DS"

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
            threading.Timer(120, encrypt_database).start()  # Re-encrypt after 120 seconds
            show_database_content()  # Show all rows of the database
        else:
            messagebox.showerror("Error", "Invalid MFA Code")
    else:
        messagebox.showerror("Error", "Invalid Username or Password")

def decrypt_database():
    with open("private.pem", "rb") as f:
        private_key = f.read()
    decrypted_file_path = decrypt_file("parking_data.db.enc", private_key, "parking_data.db")
    print("Database Decrypted. Access granted for 120 seconds.")

def encrypt_database():
    with open("public.pem", "rb") as f:
        public_key = f.read()
    encrypt_file("parking_data.db", public_key)
    print("Database Encrypted. Access revoked.")

def show_database_content():
    # Create a new window to display the database content
    data_window = tk.Toplevel()
    data_window.title("Parking Data")

    # Connect to the SQLite database
    conn = sqlite3.connect('parking_data.db')
    cursor = conn.cursor()

    # Fetch all rows from the database
    cursor.execute("SELECT * FROM parking_data")  # Removed LIMIT 5 to fetch all rows
    rows = cursor.fetchall()

    # Get column names
    columns = [description[0] for description in cursor.description]

    # Create a treeview to display the data
    tree = ttk.Treeview(data_window, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
    for row in rows:
        tree.insert("", "end", values=row)

    tree.pack(expand=True, fill="both")

    # Add a scrollbar for the treeview
    scrollbar = ttk.Scrollbar(data_window, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Add an exit button
    exit_button = tk.Button(data_window, text="Exit", command=data_window.destroy)
    exit_button.pack()

    # Close the database connection
    conn.close()

# GUI
root = tk.Tk()
root.title("Secure Database Login")

label_username = tk.Label(root, text="Username")
label_username.pack()
entry_username = tk.Entry(root)
entry_username.pack()

label_password = tk.Label(root, text="Password")
label_password.pack()
entry_password = tk.Entry(root, show="*")
entry_password.pack()

label_mfa = tk.Label(root, text="MFA Code")
label_mfa.pack()
entry_mfa = tk.Entry(root)
entry_mfa.pack()

button_login = tk.Button(root, text="Login", command=login)
button_login.pack()

root.mainloop()
