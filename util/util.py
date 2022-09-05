from datetime import datetime

import hashlib


def hash_hex(filepath):
    with open(filepath, "rb") as f:
        hash_is = hashlib.md5()
        while chunk := f.read(8192):
            hash_is.update(chunk)

    return hash_is.hexdigest()


def timestamp(sep="", splitsep="-"):
    return datetime.now().strftime(f"%Y{sep}%m{sep}%d{splitsep}%H{sep}%M{sep}%S")

# def ms2s(time):
#     return time / 1000

# def format_seconds(time):
#     return f"{time:.3f}"
