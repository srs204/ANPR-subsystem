# VecSpace Secure Database

By Sa'af Rabbi

This project provides a secure database with AES encryption reinforced with RSA and MFA, brought together conviniently with a GUI. The database is initially encrypted and can only be decrypted through assigned credentials and remote authentication. 

The database automatically encrypts itself within a set timer of 120 seconds given no additional changes are made to the database. 

This ensures Confidentiality, Integrity, and Availability (CIA) criteria of cybersecurity

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt

2. Make sure you have sqlite3 and sqlitebrowser to view and edit the database 

3. The database should initially come encrypted. If not, use the RSA_key_generator.py utility to produce the public and private keys (if there are no public/private keys in the directory). 
Now, encrypt the database using:
	python3 -c "from encrypt_decrypt import encrypt_file; encrypt_file('parking_data.db', open('public.pem', 'rb').read())"
	
4. Run the MFA_setup.py utility to generate a QR code and synchronize it with remote authenticator. Copy the MFA tag and add it to the gui_app.py script.

5. The GUI is ready to use. Username: "Vilgefortz", Password: "Gwentify"

6. After successful login and authorization, the decrypted database can be updated within the timer. After the timer runs out the updated database is encrypted and the original encrypted database is deleted

7. The GUI also prints out the rows of the database after successful authentication

8. If need arises, the database can be manually decrypted using
	python3 -c "from encrypt_decrypt import decrypt_file; decrypt_file('parking_data.db.enc', open('private.pem', 'rb').read(), 'parking_data.db')"
