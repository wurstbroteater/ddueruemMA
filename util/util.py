import hashlib
import os
import pathlib
import subprocess
from datetime import datetime


def hash_hex(filepath):
    with open(filepath, "rb") as f:

        hash_is = hashlib.md5()
        while chunk := f.read(8192):
            hash_is.update(chunk)

    return hash_is.hexdigest()


def timestamp(sep="", splitsep="-"):
    return datetime.now().strftime(f"%Y{sep}%m{sep}%d{splitsep}%H{sep}%M{sep}%S")


def ms2s(time):
    return time / 1000


def format_seconds(time):
    return f"{time:.3f}"


# ---------------------------------------------- Timing ----------------------------------------------

_running = {}


def tic(name=""):
    if name in _running:
        raise RuntimeError(f"Timer with name \"{name}\" already running")

    _running[name] = datetime.now()


def toc(name=""):
    if name not in _running:
        raise RuntimeError(f"Timer with name \"{name}\" not running")

    time = datetime.now() - _running[name]
    _running.pop(name)

    return time.total_seconds()


def peek(name=""):
    if name not in _running:
        raise RuntimeError(f"Timer with name \"{name}\" not running")

    time = datetime.now() - _running[name]

    return time.total_seconds()


# ---------------------------------------------- XML Translation ----------------------------------------------
def translate_xml(filepath, target_folder, formats):
    """Receives path to XML Feature Model, target folder to store files and list of wanted file formats"""
    path_to_jar = str(pathlib.Path(
        __file__).parent.resolve()) + os.path.sep + 'FeatureModelTransformation' + os.path.sep + 'FMTransform.jar'
    args = ['java', '-jar', path_to_jar, filepath, target_folder] + formats
    # hide normal outputs but show errors
    rc = subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    if rc == 0:
        return "Successfully translated to all formats!"
    elif rc == 1:
        return "Failed to translate file!"
    elif rc == 2:
        return "Translation to at least 1 wanted format failed!"
    else:
        return "Unknown return code: " + str(rc)
