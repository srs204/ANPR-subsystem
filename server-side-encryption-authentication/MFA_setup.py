import pyotp
import qrcode
from dotenv import set_key
import os

# Generate MFA secret
secret = pyotp.random_base32()
print("MFA Secret:", secret)

# Write to .env file
env_path = ".env"
set_key(env_path, "MFA_SECRET", secret)

# Generate QR code
uri = pyotp.totp.TOTP(secret).provisioning_uri(name="SecureDatabase", issuer_name="VecSpace AI")
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(uri)
qr.make(fit=True)
img = qr.make_image(fill='black', back_color='white')
img.save("mfa_qr.png")

print("QR code saved as mfa_qr.png. Secret written to .env.")

