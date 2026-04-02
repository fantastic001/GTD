
import os 
import shutil
import logging 

logger = logging.getLogger(__name__)

def get_attachments_dir():
    logger.debug("Getting attachments directory.")
    attachments_dir = os.path.join(os.path.expanduser("~"), ".gtd", "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    logger.debug(f"Attachments directory: {attachments_dir}")
    return attachments_dir

def attach_file(path):
    logger.debug(f"Attaching file: {path}")
    attachments_dir = get_attachments_dir()
    if not os.path.isfile(path):
        logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"The file {path} does not exist.")
    filename = os.path.basename(path)
    dest_path = os.path.join(attachments_dir, filename)
    shutil.copy2(path, dest_path)
    logger.info(f"File attached: {dest_path}")
    return dest_path