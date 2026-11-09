"""Download a file with aria2c or wget into DOWNLOAD_PATH/<folder>/, resumable."""
import logging
import os
import re
import shutil
import subprocess

from dotenv import load_dotenv

load_dotenv()

DOWNLOAD_PATH = os.path.abspath(os.path.expanduser(os.getenv("DOWNLOAD_PATH", "./downloads")))
TOOLS = ("aria2", "wget")

logger = logging.getLogger(__name__)


def sanitize(name: str) -> str:
    """Remove characters that are illegal in file names, and surrounding dots/spaces."""
    return re.sub(r'[\\/*?:"<>|]', "", name or "").strip(" .") or "untitled"


def target_dir(folder_name: str | None) -> str:
    """Create and return DOWNLOAD_PATH, or DOWNLOAD_PATH/<folder_name>."""
    path = os.path.join(DOWNLOAD_PATH, sanitize(folder_name)) if folder_name else DOWNLOAD_PATH
    os.makedirs(path, exist_ok=True)
    return path


def available_tools() -> list[str]:
    """The downloaders installed on this machine, among aria2 and wget."""
    binaries = {"aria2": "aria2c", "wget": "wget"}
    return [t for t in TOOLS if shutil.which(binaries[t])]


def build_command(tool: str, url: str, directory: str, filename: str, insecure: bool) -> list[str]:
    if tool == "aria2":
        cmd = ["aria2c", "--dir", directory, "--out", filename,
               "-x", "4", "-s", "4", "--continue=true",
               "--summary-interval=0", "--console-log-level=warn", "--download-result=hide"]
        if insecure:
            cmd.append("--check-certificate=false")
    elif tool == "wget":
        cmd = ["wget", "-c", "-O", os.path.join(directory, filename),
               "--progress=bar:force:noscroll"]
        if insecure:
            cmd.append("--no-check-certificate")
    else:
        raise ValueError(f"unknown downloader {tool!r}")
    cmd.append(url)
    return cmd


def download(tool: str, url: str, folder_name: str, filename: str, insecure: bool = False) -> bool:
    """Download `url` as `filename`; resumes a partial file. Returns True on success."""
    directory = target_dir(folder_name)
    filename = sanitize(filename)
    cmd = build_command(tool, url, directory, filename, insecure)
    logger.info("downloading %s -> %s/%s with %s", url, directory, filename, tool)
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("%s exited with code %s for %s", tool, e.returncode, url)
        return False
