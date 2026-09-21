# dev_tools/build_exe.py - package the game as one Windows .exe.
#
#   python dev_tools/build_exe.py            build dist/DontEvenBother.exe
#   python dev_tools/build_exe.py --console  keep a console window (for debugging)
#
# --onefile puts the interpreter, pygame and the game into a single file that
# players can double-click with nothing installed. At startup it unpacks
# itself into a temporary folder and deletes that on exit, which is why the
# save lives in AppData instead (see BASE_PATH / SAVE_DIR in settings.py).
#
# The ghost races replay solver runs from dev_tools/solutions, so those have
# to travel with the build; everything else the game draws is generated in
# code, so there are no other assets to carry.

import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "DontEvenBother"
SOLUTIONS = os.path.join("dev_tools", "solutions")


def main():
    parser = argparse.ArgumentParser(description="Build the game as a single .exe")
    parser.add_argument("--console", action="store_true",
                        help="keep the console window so tracebacks are visible")
    parser.add_argument("--keep-build", action="store_true",
                        help="leave PyInstaller's scratch folder behind")
    args = parser.parse_args()

    solutions = os.path.join(ROOT, SOLUTIONS)
    if not os.path.isdir(solutions):
        raise SystemExit(f"missing {SOLUTIONS} - the ghost races need it")

    # "source;destination-inside-the-bundle"; settings.BASE_PATH points at the
    # unpack folder when frozen, so this lands exactly where ghosts.py looks
    add_data = f"{solutions}{os.pathsep}{SOLUTIONS}"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", NAME,
        "--add-data", add_data,
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build", "pyinstaller"),
        "--specpath", os.path.join(ROOT, "build"),
        "--noconfirm",
        # the save must never be baked into the bundle, and the tests and
        # build tools are not part of the game
        "--exclude-module", "pytest",
        "--exclude-module", "tkinter",
        # PyInstaller drags pkg_resources in by dependency scan and then its
        # runtime hook dies looking for jaraco, which is not installed. The
        # game never imports any of it, so it simply should not be here.
        "--exclude-module", "pkg_resources",
        "--exclude-module", "setuptools",
    ]
    if not args.console:
        cmd.append("--windowed")
    icon = os.path.join(ROOT, "icon.ico")
    if os.path.exists(icon):
        cmd += ["--icon", icon]
    cmd.append(os.path.join(ROOT, "main.py"))

    print(" ".join(cmd))
    started = time.time()
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(f"PyInstaller failed ({result.returncode})")

    exe = os.path.join(ROOT, "dist", NAME + ".exe")
    if not os.path.exists(exe):
        raise SystemExit("PyInstaller reported success but produced no .exe")
    size = os.path.getsize(exe) / (1024 * 1024)
    print(f"\nbuilt {exe}")
    print(f"  {size:.1f} MB, in {time.time() - started:.0f}s")
    print("  saves go to %APPDATA%\\DontEvenBother, so progress survives")

    if not args.keep_build:
        shutil.rmtree(os.path.join(ROOT, "build", "pyinstaller"), ignore_errors=True)


if __name__ == "__main__":
    main()
