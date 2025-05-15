# VecSpace Secure Database

By Sa'af Rabbi

This project provides a secure, user-friendly database interface combining AES file encryption, RSA key security, and time-based MFA authentication. The system is wrapped in a sleek GUI using `ttkbootstrap` and ensures confidentiality, integrity, and availability (CIA) through automatic encryption and secure access control.

---

## 🔐 Features

- 🔒 AES encryption with RSA key wrapping
- 🔐 Multi-Factor Authentication using TOTP (e.g., Google Authenticator)
- 🔁 Automatic encryption 120 seconds after login
- 🧪 RSA key generator utility
- 📦 MFA setup with `.env` sync (no manual editing required)
- 🖥️ GUI built with `ttkbootstrap` for a clean, modern interface
- 📂 SQLite database viewer with read access post-authentication

---

## 📦 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> Use a virtual environment (`python3 -m venv venv`) if preferred.

---

### 2. Generate RSA Keys (if not present)

```bash
python3 RSA_key_generator.py
```

This creates:
- `public.pem` (used for encrypting the AES key)
- `private.pem` (used for decrypting the AES key)

---

### 3. Prepare the Database

Make sure you have a SQLite database file named `parking_data.db`.

Then encrypt it:

```bash
python3 -c "from encrypt_decrypt import encrypt_file; encrypt_file('parking_data.db', open('public.pem', 'rb').read())"
```

This generates `parking_data.db.enc` and deletes the unencrypted one.

---

### 4. Set Up MFA

Run:

```bash
python3 MFA_setup.py
```

This will:
- Generate a TOTP secret
- Save it into `.env` (no need to manually copy anything)
- Create `mfa_qr.png` — scan it with Google Authenticator or similar

---

### 5. Run the GUI

```bash
python3 gui_app.py
```

> Credentials:  
> **Username:** `Vilgefortz`  
> **Password:** `Gwentify`

You’ll also need the correct MFA code from your authenticator.

---

### 6. What Happens After Login?

- The database is decrypted temporarily
- All rows are displayed in a new window
- After 120 seconds, the database is re-encrypted and the decrypted file is deleted

---

### 7. Manual Decryption (if needed)

```bash
python3 -c "from encrypt_decrypt import decrypt_file; decrypt_file('parking_data.db.enc', open('private.pem', 'rb').read(), 'parking_data.db')"
```

---

## 🧪 Optional Tools

- **DB Viewer:** You may use GUI tools like `sqlitebrowser` to inspect `parking_data.db` (after decryption).

---

## ✅ Security Practices

- MFA secrets stored via `.env` (never hardcoded)
- Encrypted database never left in plaintext beyond timeout
- RSA 2048-bit key wrapping for AES-256 encryption

---

Feel free to fork and enhance. For contributions or issues, contact the author.