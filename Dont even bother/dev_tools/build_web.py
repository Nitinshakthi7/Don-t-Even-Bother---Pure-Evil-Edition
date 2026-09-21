# dev_tools/build_web.py - package the game for browsers with pygbag.
#
#   python dev_tools/build_web.py           build into build/web
#   python dev_tools/build_web.py --serve   build and serve it on localhost:8000
#
# pygbag packs every file in the folder you point it at, which on a working
# copy means your personal save, its backups and the test suite all end up
# inside the download. This stages a clean copy first and ships only what the
# game needs to run: the modules, and the solver replays the ghost races use.

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The folder name becomes the bundle name the browser downloads, and browsers
# cache that file hard. A version in the name makes every build a new URL, so
# "I tested it" always means the build you just made.
VERSION = os.environ.get("WEB_BUILD_TAG", "v2")
STAGE = os.path.join(ROOT, "build", f"deb-{VERSION}")

# what the browser build actually needs
KEEP_DIRS = [os.path.join("dev_tools", "solutions")]       # ghost racing reads these
SKIP_NAMES = {"build", "__pycache__", "tests", ".git"}
SKIP_SUFFIX = (".pyc", ".md", ".txt")


def should_skip(name):
    if name in SKIP_NAMES or name.endswith(SKIP_SUFFIX):
        return True
    # never ship anyone's save, or a backup of it
    return name.startswith("rage_save")


def stage():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    shipped = 0
    for name in sorted(os.listdir(ROOT)):
        if should_skip(name):
            continue
        source = os.path.join(ROOT, name)
        if os.path.isfile(source) and name.endswith(".py"):
            shutil.copy2(source, os.path.join(STAGE, name))
            shipped += 1
    for relative in KEEP_DIRS:
        source = os.path.join(ROOT, relative)
        if not os.path.isdir(source):
            continue
        target = os.path.join(STAGE, relative)
        shutil.copytree(source, target)
        shipped += sum(len(files) for _, _, files in os.walk(target))
    return shipped


def port_is_busy(port):
    """True if something already listens on the port."""
    with socket.socket() as probe:
        probe.settimeout(0.4)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def write_host_config(web_dir):
    """Drop a vercel.json next to the built page.

    The bundle name carries a version so it can be cached hard, but index.html
    must not be: it is the file that points at the new bundle, and a cached
    copy is how you end up testing a build you replaced an hour ago.
    """
    config = {
        "headers": [
            {"source": "/index.html",
             "headers": [{"key": "Cache-Control", "value": "no-cache, must-revalidate"}]},
            {"source": "/(.*)\.(apk|tar\.gz)",
             "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
        ]
    }
    path = os.path.join(web_dir, "vercel.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="Build the browser version.")
    parser.add_argument("--serve", action="store_true", help="serve it on localhost:8000 afterwards")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    count = stage()
    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(STAGE) for f in fs)
    print(f"staged {count} files, {size / 1024:.0f} KB, in {STAGE}")

    leaked = [f for r, _, fs in os.walk(STAGE) for f in fs if f.startswith("rage_save")]
    if leaked:
        raise SystemExit(f"refusing to build: a save file got staged ({leaked})")

    if args.serve and port_is_busy(args.port):
        raise SystemExit(f"""refusing to serve: port {args.port} is already taken.
  That is almost certainly an older build server. Leave it running and it
  keeps answering with the OLD build while you think you are testing the
  new one. Stop it, or pass --port with a free one.""")

    cmd = [sys.executable, "-m", "pygbag", "--ume_block", "0", "--port", str(args.port)]
    if not args.serve:
        cmd.append("--build")
    cmd.append(STAGE)
    print(" ".join(cmd))
    subprocess.run(cmd, check=False)

    web_dir = os.path.join(STAGE, "build", "web")
    if os.path.isdir(web_dir):
        write_host_config(web_dir)
        print()
        print("deploy this folder:")
        print(f"  {web_dir}")
        print(f"  npx vercel deploy --prod {web_dir}")


if __name__ == "__main__":
    main()
