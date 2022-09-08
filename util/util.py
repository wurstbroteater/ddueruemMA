from datetime import datetime

import hashlib, os, pathlib, subprocess


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
