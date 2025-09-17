
from textwrap import TextWrapper
from typing import Optional
from gtd.ods import ODSDocument
import os
import tempfile
import subprocess
import pandas as pd 
from gtd.config import get_config_str, get_config_list
class Spreadsheet(object):
    def __init__(self, path: str) -> None:
        if not path.endswith(".ods"):
            path = path + ".ods"
        self.path = path
    def copy(self, destination: str):
        cmd = [
            "rclone", 
            "copy", 
            "drive:/%s" % self.path, 
            destination,
            "--drive-export-formats",
            "ods,odt,odp"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Command rclone failed to copy file %s to %s" % (self.path, destination))
        return os.path.join(destination, os.path.basename(self.path))

    def open(self, sheet_name) -> ODSDocument:
        destination = tempfile.mkdtemp()
        fullpath = self.copy(destination)
        return ODSDocument(fullpath, sheet_name)
    
    def open_pandas(self, sheet_name: str) -> pd.DataFrame:
        destination = tempfile.mkdtemp()
        fullpath = self.copy(destination)
        return pd.read_excel(fullpath, engine="odf", sheet_name=sheet_name)

class TextDocument(object):
    def __init__(self, path: str) -> None:
        if not path.endswith(".txt"):
            path = path + ".txt"
        self.path = path
    def copy(self, destination: str):
        cmd = [
            "rclone", 
            "copy", 
            "drive:/%s" % self.path, 
            destination,
            "--drive-export-formats",
            "txt"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Command rclone failed to copy file %s to %s" % (self.path, destination))
        return os.path.join(destination, os.path.basename(self.path))

    def open(self):
        try:
            destination = tempfile.mkdtemp()
            fullpath = self.copy(destination)
            return open(fullpath, "r")
        except RuntimeError:
            return None

def list_folder(folder_path: str) -> list[str]:
    cmd = [
        "rclone",
        "lsf",
        "drive:/%s" % folder_path,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, _ = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("Command rclone failed to list folder %s" % folder_path)
    files = out.decode("utf-8").split("\n")
    # remove extension part 
    files = [os.path.splitext(f)[0] for f in files if f.strip() != ""]
    # remove trailing slash for folders
    files = [f[:-1] if f.endswith("/") else f for f in files]
    return files

def search_text_documents(filename: str, search_paths: list[str]) -> list[TextDocument]:
    result = [] 
    for path in search_paths:
        fullpath = os.path.join(path, filename)
        text = TextDocument(fullpath)
        try:
            f = text.open()
            if f is not None:
                f.close()
                result.append(text)
        except RuntimeError:
            continue
    return result

def get_context_for_project(project_name: str) -> str:
    search_paths = get_config_list("context_search_paths", [
        "Administration",
        "",
        "Administration/Research & Development",
        "Administration/Training & Education",
        "Administration/Social Responsibility"
    ], "Paths to search for context text files for projects on Google Drive")
    folders_to_search = [] 
    for path in search_paths:
        folders = list_folder(path)
        for folder in folders:
            if folder.lower() == project_name.lower():
                folders_to_search.append(os.path.join(path, folder))
    context_filenames = get_config_list("context_filenames", ["Context"], "Filenames to search for context text files for projects on Google Drive")
    texts = []
    for context_filename in context_filenames:
        texts.extend(search_text_documents(context_filename, folders_to_search))
    result = [] 
    for text in texts:
        f = text.open()
        if f is not None:
            content = f.read().strip()
            f.close()
            if content != "":
                result.append("\n%s" % (content))
    return "\n\n".join(result)

if __name__ == "__main__":
    print(get_context_for_project("PhD"))
