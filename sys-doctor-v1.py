#!/usr/bin/env python3
# sys-doctor.py
# Smart Linux System Health Analyzer (CPU / GPU / RAM / Disk)

import subprocess
import shutil
import os
import sys
from datetime import datetime

# =========================
# Utils
# =========================

def run(cmd):
    return subprocess.getoutput(cmd).strip()

def exists(cmd):
    return shutil.which(cmd) is not None

def require_root():
    if os.geteuid() != 0:
        print("❌ Please run with sudo")
        sys.exit(1)

def ask(msg):
    return input(msg).lower().startswith("y")

# =========================
# Tools per test (UX FIX)
# =========================

TOOLS_BY_TEST = {
    "cpu": {
        "lscpu": "util-linux"
    },
    "gpu": {
        "lspci": "pciutils",
        "lsmod": "kmod",
        "glxinfo": "mesa-utils"
    },
    "ram": {},
    "disk": {
        "lsblk": "util-linux",
        "smartctl": "smartmontools"
    }
}

# =========================
# Test selection
# =========================

def choose_tests():
    print("\nSelect tests to run:")
    print("1) CPU")
    print("2) GPU")
    print("3) RAM")
    print("4) Disk (SMART)")
    print("5) Full system")

    choice = input("Your choice [1-5]: ").strip()

    if choice == "1":
        return ["cpu"]
    elif choice == "2":
        return ["gpu"]
    elif choice == "3":
        return ["ram"]
    elif choice == "4":
        return ["disk"]
    elif choice == "5":
        return ["cpu", "gpu", "ram", "disk"]
    else:
        return []

# =========================
# Prepare only needed tools
# =========================

def prepare_environment(tests):
    needed = {}
    for t in tests:
        needed.update(TOOLS_BY_TEST.get(t, {}))

    missing = {c: p for c, p in needed.items() if not exists(c)}

    if not missing:
        return True

    print("\n⚠️ Missing tools for selected tests:")
    for c, p in missing.items():
        print(f" - {c} ({p})")

    if ask("Install missing tools now? [y/N]: "):
        require_root()
        pkgs = " ".join(set(missing.values()))
        subprocess.run(f"apt install -y {pkgs}", shell=True)
        return True
    else:
        print("ℹ️ Skipping related tests.")
        return False

# =========================
# CPU
# =========================

def cpu_info():
    model = run("lscpu | grep 'Model name'").split(":", 1)[1].strip()
    cores = int(run("lscpu | grep '^CPU(s):'").split()[-1])
    max_mhz = run("lscpu | grep 'max MHz'")
    max_mhz = float(max_mhz.split()[-1]) if max_mhz else 0
    return model, cores, max_mhz

def cpu_score(cores, mhz):
    score = 10 if cores >= 4 else 5
    score += 10 if mhz >= 3000 else 5
    return min(score, 25)

# =========================
# GPU
# =========================

def gpu_info():
    gpu = run("lspci | egrep -i 'vga|3d|display'")
    renderer = run("glxinfo 2>/dev/null | grep 'OpenGL renderer'")
    return gpu, renderer

def gpu_score(gpu, renderer):
    score = 0
    if "nvidia" in gpu.lower() or "amd" in gpu.lower():
        score += 10
    elif "intel" in gpu.lower():
        score += 7
    else:
        score += 3

    if renderer and "llvmpipe" not in renderer.lower():
        score += 10
    else:
        score += 3

    return min(score, 25)

# =========================
# RAM
# =========================

def ram_info():
    total_kb = int(run("grep MemTotal /proc/meminfo").split()[1])
    return round(total_kb / 1024 / 1024, 1)

def ram_score(gb):
    if gb >= 16:
        return 20
    elif gb >= 8:
        return 13
    elif gb >= 4:
        return 8
    else:
        return 4

# =========================
# Disk
# =========================

def disk_health():
    disks = run("lsblk -nd -o NAME").splitlines()
    for d in disks:
        out = run(f"smartctl -H /dev/{d}")
        if "FAILED" in out:
            return "Failing"
    return "Healthy"

def disk_score(status):
    return 20 if status == "Healthy" else 8

# =========================
# AI Suggestions
# =========================

def ai_suggestions(cpu, gpu, ram, disk):
    tips = []
    if cpu < 12:
        tips.append("CPU is aging. Consider upgrading in the future.")
    if gpu < 12:
        tips.append("GPU is outdated. Upgrade recommended for graphics.")
    if ram < 13:
        tips.append("Upgrade RAM to at least 8–16 GB.")
    if disk < 15:
        tips.append("Disk health warning. Backup data and replace disk.")
    if not tips:
        tips.append("System is well balanced. No upgrade needed now.")
    return tips

# =========================
# MAIN
# =========================

def main():
    print("🐧 sys-doctor v1.1")
    print("Smart Linux System Health Analyzer")
    print("-" * 45)

    tests = choose_tests()
    if not tests:
        print("❌ Invalid choice")
        return

    ready = prepare_environment(tests)

    cpu_s = gpu_s = ram_s = disk_s = 0
    report = []

    if "cpu" in tests:
        model, cores, mhz = cpu_info()
        cpu_s = cpu_score(cores, mhz)
        report.append(f"CPU : {model} ({cpu_s}/25)")

    if "gpu" in tests:
        gpu, renderer = gpu_info()
        gpu_s = gpu_score(gpu, renderer)
        report.append(f"GPU : {gpu_s}/25")

    if "ram" in tests:
        gb = ram_info()
        ram_s = ram_score(gb)
        report.append(f"RAM : {gb} GB ({ram_s}/20)")

    if "disk" in tests and ready:
        status = disk_health()
        disk_s = disk_score(status)
        report.append(f"Disk: {status} ({disk_s}/20)")

    total = cpu_s + gpu_s + ram_s + disk_s

    print("\n🧾 RESULTS")
    print("-" * 30)
    for r in report:
        print(r)

    print(f"\nTOTAL SCORE: {total}/100")

    print("\nAI SUGGESTIONS:")
    for tip in ai_suggestions(cpu_s, gpu_s, ram_s, disk_s):
        print(f"- {tip}")

if __name__ == "__main__":
    main()
