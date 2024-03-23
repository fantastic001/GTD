
from gtd.ods import ODSDocument
import os
import tempfile
import subprocess
import pandas as pd 
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