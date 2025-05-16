script = """#!/usr/bin/env python3
\"\"\"security_assessment.py

Run network, application, database, and host security checks.
Usage:
    security_assessment.py network 10.60.35.245 10.60.35.183
    security_assessment.py app /path/to/code
    security_assessment.py db --host 10.60.35.183 --user jetson --password Amelie_2001 --url http://10.60.35.245:5000/api/parking-data?start_date=2025-05-01
    security_assessment.py host
    security_assessment.py all --targets 10.60.35.245 10.60.35.183 --path . --host 10.60.35.183 --user jetson --password Amelie_2001 --url <API_URL>
\"\"\"

import argparse
import subprocess
import sys
import os

def run_subprocess(cmd):
    print(f\"\\n[*] Running: {' '.join(cmd)}\")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f\"[!] Error running {' '.join(cmd)}\", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)

def network_scan(targets):
    # Nmap service/version detection
    run_subprocess(['nmap', '-sV', '-p', '22,80,443,5000,3306'] + targets)
    # Host hardening check (Lynis)
    run_subprocess(['lynis', 'audit', 'system'])

def app_static_scan(path):
    # Python security linting
    run_subprocess(['bandit', '-r', path])

def db_assessment(host, user, password, url):
    # Check DB grants
    grant_cmd = ['mysql', f'-h{host}', f'-u{user}', f'-p{password}', '-e', f\"SHOW GRANTS FOR '{user}'@'10.60.35.%';\"]
    run_subprocess(grant_cmd)
    # SQLMap injection test
    if url:
        run_subprocess(['sqlmap', '-u', url, '--batch', '--dbs'])
    else:
        print('[*] No URL provided for SQLMap.')

def host_checks():
    # Firewall status
    run_subprocess(['ufw', 'status'])
    # List iptables
    run_subprocess(['iptables', '-L', '-n', '-v'])

def main():
    parser = argparse.ArgumentParser(description='Security Assessment Tool')
    subparsers = parser.add_subparsers(dest='command')

    net = subparsers.add_parser('network', help='Run network scans')
    net.add_argument('targets', nargs='+', help='Target IPs')

    app = subparsers.add_parser('app', help='Run application static scan')
    app.add_argument('path', help='Path to code directory')

    db = subparsers.add_parser('db', help='Run database assessment')
    db.add_argument('--host', default='10.60.35.183')
    db.add_argument('--user', default='jetson')
    db.add_argument('--password', default='Amelie_2001')
    db.add_argument('--url', help='API endpoint URL for SQLMap')

    srv = subparsers.add_parser('host', help='Run host firewall and iptables checks')

    allp = subparsers.add_parser('all', help='Run all assessments')
    allp.add_argument('--targets', nargs='+', default=['10.60.35.245', '10.60.35.183'])
    allp.add_argument('--path', default='.')
    allp.add_argument('--host', default='10.60.35.183')
    allp.add_argument('--user', default='jetson')
    allp.add_argument('--password', default='Amelie_2001')
    allp.add_argument('--url', help='API endpoint URL for SQLMap')

    args = parser.parse_args()

    if args.command == 'network':
        network_scan(args.targets)
    elif args.command == 'app':
        app_static_scan(args.path)
    elif args.command == 'db':
        db_assessment(args.host, args.user, args.password, args.url)
    elif args.command == 'host':
        host_checks()
    elif args.command == 'all':
        network_scan(args.targets)
        app_static_scan(args.path)
        db_assessment(args.host, args.user, args.password, args.url)
        host_checks()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
"""
# Write the script to disk
with open('/mnt/data/security_assessment.py', 'w') as f:
    f.write(script)
# Make it executable
os.chmod('/mnt/data/security_assessment.py', 0o755)
print("Created executable at /mnt/data/security_assessment.py")

