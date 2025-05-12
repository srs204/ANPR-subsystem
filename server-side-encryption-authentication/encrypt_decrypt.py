from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
import os

def encrypt_file(file_path, public_key):
    # Generating our random AES key
    aes_key = get_random_bytes(32)  # 256-bit key for AES

    # Encrypting with AES
    cipher_aes = AES.new(aes_key, AES.MODE_EAX)
    with open(file_path, "rb") as f:
        data = f.read()
    ciphertext, tag = cipher_aes.encrypt_and_digest(data)

    # Encrypting the AES key with RSA
    rsa_key = RSA.import_key(public_key)
    cipher_rsa = PKCS1_OAEP.new(rsa_key)
    encrypted_aes_key = cipher_rsa.encrypt(aes_key)

    # Saving the encrypted file metadata
    encrypted_file_path = file_path + ".enc"
    with open(encrypted_file_path, "wb") as f:
        [f.write(x) for x in (encrypted_aes_key, cipher_aes.nonce, tag, ciphertext)]

    os.remove(file_path)  # Removing the original unencrypted file
    return encrypted_file_path

def decrypt_file(encrypted_file_path, private_key, output_file_path):
    # Reading the encrypted file metadata
    with open(encrypted_file_path, "rb") as f:
        encrypted_aes_key = f.read(256)  # RSA-encrypted AES key
        nonce = f.read(16)  # AES nonce
        tag = f.read(16)  # AES tag
        ciphertext = f.read()  # AES-encrypted data

    # Decrypting the AES key with RSA
    rsa_key = RSA.import_key(private_key)
    cipher_rsa = PKCS1_OAEP.new(rsa_key)
    aes_key = cipher_rsa.decrypt(encrypted_aes_key)

    # Decrypting the file with AES
    cipher_aes = AES.new(aes_key, AES.MODE_EAX, nonce)
    data = cipher_aes.decrypt_and_verify(ciphertext, tag)

    # Saving the decrypted file
    with open(output_file_path, "wb") as f:
        f.write(data)

    return output_file_path
