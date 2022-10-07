from os import path
import subprocess
import requests
import hashlib
import tarfile

from cli import cli

import config


def filter(ls, attrs):
    attrs.append("STUB")
    out = {}

    for x in ls:
        valid = True

        for attr in attrs:
            if not hasattr(x, attr):
                valid = False
                break

        if valid:
            out[x.STUB] = x

    return out


def install(tool, clean=False):
    if clean:
        cli.say("Clean installing", cli.highlight(tool.FULL))
    else:
        cli.say("Installing", cli.highlight(tool.FULL))

    if check_key(tool, "shared_lib"):
        if path.exists(tool.shared_lib):
            if clean:
                cli.say(f"Ignoring existing shared library", cli.highlight(tool.shared_lib))
            else:
                cli.say(cli.highlight(tool.shared_lib), "already exists. Nothing to do.", origin=tool.FULL)
                return True, False

    else:
        if path.exists(tool.tool_dir):
            if clean:
                cli.say(f"Please remove the directory", cli.highlight(tool.tool_dir),
                        "yourself for data security reasons")
                return True, False
            else:
                # TODO: Add a verification hooked in the plugin.
                cli.say(f"Files exist. Nothing to do.", origin=tool.FULL)
                return True, False

    if check_key(tool, "url"):

        archive_path = path.join(config.DIR_ARCHIVES, tool.archive)
        sources_path = path.join(config.DIR_ARCHIVES, tool.sources_dir)

        if clean or not path.exists(archive_path):
            cli.say("Downloading", cli.highlight(tool.url))
            download(tool.url, archive_path)

        if clean or not path.exists(sources_path):
            valid, reason = verify_hash(archive_path, tool.archive_md5)

            if not valid:
                error(reason)

            cli.say(f"Unpacking", cli.highlight(tool.archive))
            untar(archive_path)

    elif check_key(tool, "git_url"):
        if not path.exists(tool.tool_dir):
            cli.say("Cloning", cli.highlight(tool.git_url))
            subprocess.run(["git", "clone", tool.git_url, tool.tool_dir], capture_output=True)

    if check_key(tool, "shared_lib"):
        if clean or not path.exists(tool.shared_lib):
            cli.say("Configuring...", end=" ")
            ec, stdout, stderr = tool.configure()

            if ec != 0:
                cli.error("Failed")
                cli.error("Configuring failed with exit code", cli.highlight(ec))
                cli.say(stdout)
                cli.say(stderr)
                return False, False
            else:
                cli.say("Done.")

            cli.say("Making...", end=" ")

            proc = subprocess.run(['make', tool.make_append, tool.STUB.lower(), '-j4'], capture_output=True)
            ec = proc.returncode
            stdout = proc.stdout.decode("utf-8")
            stderr = proc.stderr.decode("utf-8")

            if ec != 0:
                cli.error("Failed")
                cli.error("Making failed with exit code", cli.highlight(ec))
                cli.say(stdout)
                cli.say(stderr)
                return False, False
            else:
                cli.say("Done.")

        if path.exists(tool.shared_lib):
            cli.say(cli.highlight(tool.FULL), 'build: SUCCESS')
        else:
            cli.say(cli.highlight(tool.FULL), 'build: FAIL')
    elif check_key(tool, "tool_exe"):
        tool.build()

    return True, True


### Download
def untar(filepath):
    with tarfile.open(filepath) as archive:
        archive.extractall(path=config.DIR_ARCHIVES)


def download(url, target):
    req = requests.get(url)

    with open(target, "wb") as file:
        file.write(req.content)


### Hashing

def hash_hex(filepath):
    with open(filepath, "rb") as f:
        hash_is = hashlib.md5()
        while chunk := f.read(8192):
            hash_is.update(chunk)

    return hash_is.hexdigest()


def verify_hash(filepath, hash_should):
    hash_is = hash_hex(filepath)

    if hash_is == hash_should:
        return (True, "")
    else:
        return (False, f"Hash of {filepath} ({hash_is}) does not match expected hash ({hash_should})")


def check_key(obj, key):
    return getattr(obj, key, None)
