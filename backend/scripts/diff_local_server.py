"""对比本地与服务器工作区文件内容差异"""
import hashlib
import subprocess

# 服务器上 git status --short 的文件列表（从远程取）
remote = subprocess.run(
    ["ssh", "almd@43.143.253.186",
     "cd /home/almd/prcp && git status --short"],
    capture_output=True, text=True,
).stdout.strip().splitlines()

server_modified = []   # M - 已修改
server_untracked = []  # ?? - 新增
for line in remote:
    line = line.rstrip()
    if not line:
        continue
    st, path = line[:2].strip(), line[3:].strip()
    if st == "M":
        server_modified.append(path)
    elif st == "??":
        server_untracked.append(path)

print(f"服务器已修改: {len(server_modified)}　新增: {len(server_untracked)}\n")


def md5_local(path):
    try:
        with open(f"C:/银行经营/PRCP/{path}", "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def md5_server(path):
    r = subprocess.run(
        ["ssh", "almd@43.143.253.186", f"md5sum '/home/almd/prcp/{path}'"],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    return out.split()[0] if out else None


print("=== 已修改文件：本地 vs 服务器 ===")
same, diff, only_local, only_server = [], [], [], []
for p in server_modified:
    hl, hs = md5_local(p), md5_server(p)
    if hl is None:
        only_server.append(p); tag = "仅服务器有"
    elif hl == hs:
        same.append(p); tag = "一致"
    else:
        diff.append(p); tag = "★内容不同"
    print(f"  {tag:<10} {p}")

print("\n=== 新增文件（服务器有，本地是否有）===")
for p in server_untracked[:40]:
    hl = md5_local(p)
    if hl is None:
        only_server.append(p); print(f"  仅服务器有  {p}")
    else:
        hs = md5_server(p)
        (same if hl == hs else diff).append(p)
        print(f"  {'一致' if hl == hs else '★内容不同':<10}  {p}")

print("\n" + "=" * 60)
print(f"一致       : {len(same)}")
print(f"内容不同   : {len(diff)}")
print(f"仅服务器有 : {len(only_server)}")
if diff:
    print("\n内容不同的文件（需人工确认）:")
    for p in diff:
        print("  -", p)
if only_server:
    print("\n仅服务器有的文件（本地缺失，必须先下载）:")
    for p in only_server:
        print("  -", p)