
import os 
import shutil

def get_attachments_dir():
    attachments_dir = os.path.join(os.path.expanduser("~"), ".gtd", "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    return attachments_dir

def attach_file(path):
    attachments_dir = get_attachments_dir()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"The file {path} does not exist.")
    filename = os.path.basename(path)
    dest_path = os.path.join(attachments_dir, filename)
    shutil.copy2(path, dest_path)
    return dest_path