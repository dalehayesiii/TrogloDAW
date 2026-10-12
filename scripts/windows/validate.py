"""Validate the embedded Windows Python bundle from Linux."""

import sys, re
from pathlib import Path
import pefile
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

root = Path(sys.argv[1])  # .../TrogloDAW
py = root / "python"
sp = py / "Lib" / "site-packages"
problems = []
# 1. wheel tags
tags = {}
for wf in sp.glob("*.dist-info/WHEEL"):
    t = [l.split(":", 1)[1].strip() for l in wf.read_text().splitlines() if l.startswith("Tag:")]
    tags[wf.parent.name] = t
    if not all(x.endswith("-any") or x.endswith("win_amd64") for x in t):
        problems.append(f"bad wheel tag {wf.parent.name}: {t}")
    if any(
        "cp3" in x and not ("cp312" in x or "abi3" in x or "py3" in x.split("-")[0])
        for x in t
        if not x.endswith("-any")
    ):
        problems.append(f"non-cp312 tag {wf.parent.name}: {t}")
print(
    f"[1] {len(tags)} dists; binary(win_amd64): {sum(1 for t in tags.values() if any('win_amd64' in x for x in t))}, pure: {sum(1 for t in tags.values() if all(x.endswith('-any') for x in t))}"
)
# 2. binary formats
elf = macho = pe_bad = 0
pe_ok = 0
pes = []
for f in root.rglob("*"):
    if not f.is_file():
        continue
    with open(f, "rb") as h:
        head = h.read(4)
    if head == b"\x7fELF":
        elf += 1
        problems.append(f"ELF binary: {f}")
    elif head in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xcf"):
        macho += 1
        problems.append(f"Mach-O: {f}")
    elif head[:2] == b"MZ" and f.suffix.lower() in (".pyd", ".dll", ".exe"):
        try:
            pe = pefile.PE(str(f), fast_load=True)
            if pe.FILE_HEADER.Machine != 0x8664:
                pe_bad += 1
                problems.append(f"non-x64 PE: {f}")
            else:
                pe_ok += 1
                pes.append((f, pe))
        except Exception as e:
            problems.append(f"PE parse fail {f}: {e}")
so = list(root.rglob("*.so")) + list(root.rglob("*.dylib"))
problems += [f"non-Windows shared library: {f}" for f in so]
print(
    f"[2] x64 PE files: {pe_ok}, non-x64 PE: {pe_bad}, ELF: {elf}, Mach-O: {macho}, *.so/*.dylib files: {len(so)}"
)
# 3. DLL import resolution
SYSTEM = {
    d.lower()
    for d in """kernel32.dll user32.dll advapi32.dll shell32.dll ole32.dll oleaut32.dll ws2_32.dll gdi32.dll
comdlg32.dll comctl32.dll winmm.dll shlwapi.dll version.dll crypt32.dll bcrypt.dll ntdll.dll secur32.dll rpcrt4.dll
iphlpapi.dll userenv.dll psapi.dll dbghelp.dll setupapi.dll imm32.dll winhttp.dll wininet.dll ncrypt.dll mswsock.dll
dwmapi.dll uxtheme.dll avrt.dll mfplat.dll mf.dll mfreadwrite.dll mfuuid.dll propsys.dll dsound.dll dxgi.dll d3d11.dll
msacm32.dll ksuser.dll uiautomationcore.dll powrprof.dll cfgmgr32.dll hid.dll normaliz.dll wldap32.dll dnsapi.dll
api-ms-win-core-synch-l1-2-0.dll ucrtbase.dll msvcrt.dll opengl32.dll glu32.dll mmdevapi.dll winspool.drv
netapi32.dll mpr.dll wtsapi32.dll credui.dll cryptbase.dll sspicli.dll wintrust.dll imagehlp.dll
cabinet.dll msi.dll bcryptprimitives.dll combase.dll pdh.dll avicap32.dll""".split()
}
names_by_dir = {}
for f, _ in pes:
    names_by_dir.setdefault(f.parent, set()).add(f.name.lower())
all_bundled = {f.name.lower() for f, _ in pes}
missing = {}
for f, pe in pes:
    pe.parse_data_directories(
        directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ]
    )
    imps = [e.dll.decode().lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
    imps += [e.dll.decode().lower() for e in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]
    for d in imps:
        if d in SYSTEM or d.startswith("api-ms-win-") or d.startswith("ext-ms-"):
            continue
        if d in all_bundled:
            continue
        missing.setdefault(d, []).append(str(f.relative_to(root)))
print(
    "[3] DLL imports not bundled and not core Windows:",
    {k: (len(v), v[:3]) for k, v in missing.items()} or "none",
)
for k in missing:
    problems.append(f"unresolved DLL {k} needed by {missing[k][:3]}")
# 4. requirement markers under a Windows/cp312 environment
env = {
    "sys_platform": "win32",
    "platform_system": "Windows",
    "os_name": "nt",
    "platform_machine": "AMD64",
    "python_version": "3.12",
    "python_full_version": "3.12.10",
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
    "extra": "",
}
installed = {}
for md in sp.glob("*.dist-info/METADATA"):
    txt = md.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^Name: (.+)$", txt, re.M)
    if match is None:
        problems.append(f"package metadata missing Name: {md}")
        continue
    name = canonicalize_name(match.group(1))
    installed[name] = txt
unmet = []
for name, txt in installed.items():
    for line in re.findall(r"^Requires-Dist: (.+)$", txt, re.M):
        r = Requirement(line)
        if r.marker and not r.marker.evaluate(env):
            continue
        if canonicalize_name(r.name) not in installed:
            unmet.append(f"{name} -> {line}")
print("[4] unmet Windows requirements:", unmet or "none")
problems += [f"unmet {u}" for u in unmet]
# 5. ffmpeg
ff = list(sp.glob("imageio_ffmpeg/binaries/*"))
print("[5] imageio-ffmpeg binaries:", [p.name for p in ff])
if not any(p.suffix.lower() == ".exe" for p in ff):
    problems.append("bundled Windows ffmpeg executable missing")
print("[6] soundfile data:", [p.name for p in (sp / "_soundfile_data").glob("*")])
print("\nPROBLEMS:" if problems else "\nALL CHECKS PASSED", *problems[:40], sep="\n  ")
sys.exit(1 if problems else 0)
