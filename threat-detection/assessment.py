import subprocess

# Function to run nmap scan
def nmap_scan(target_ip):
    subprocess.run(['nmap', '-sV', '-p', '1-65535', target_ip])

# Function to run sqlmap
def sqlmap_scan(api_url):
    subprocess.run(['sqlmap', '-u', api_url, '--dbs'])

# Run tests
if __name__ == "__main__":
    jetson_ip = "10.60.35.245"
    pi_ip = "10.60.35.183"
    api_endpoint = "http://10.60.35.245:5000/api/parking-data?start_date=2023-01-01"

    print("Starting Nmap scans...")
    nmap_scan(jetson_ip)
    nmap_scan(pi_ip)

    print("Starting SQL Injection tests...")
    sqlmap_scan(api_endpoint)
