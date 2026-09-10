import subprocess
sql = 'SELECT id, node_code, scheme_id FROM prcp_coa_node WHERE id IN (70,71,72)'
cmd = ['ssh', '-o', 'ConnectTimeout=10', '-tt', '-p', '22', 'almd@43.143.253.186',
        f"echo 'almd' | sudo -S mysql prcp_db -B -e \"{sql}\""]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
for l in r.stdout.split('\n'):
    s = l.strip()
    if not s: continue
    if 'ubuntu' in s.lower(): continue
    if 'documentation' in s.lower(): continue
    if 'updates' in s.lower(): continue
    if 'security' in s.lower(): continue
    if 'processes' in s.lower(): continue
    if 'usage of' in s.lower(): continue
    if 'system information' in s.lower(): continue
    if 'support' in s.lower(): continue
    if 'management' in s.lower(): continue
    if 'users logged' in s.lower(): continue
    if 'sudo' in s.lower(): continue
    print(s)