import pyotp
import qrcode

# Generating the secret key for MFA
secret = pyotp.random_base32()
print("MFA Secret:", secret)

# Generating a QR code for the user to scan
uri = pyotp.totp.TOTP(secret).provisioning_uri(name="SecureDatabase", issuer_name="VecSpace AI")
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(uri)
qr.make(fit=True)
img = qr.make_image(fill='black', back_color='white')
img.save("mfa_qr.png")
print("QR code saved as mfa_qr.png. Scan it with your authenticator app.")
