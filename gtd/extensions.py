
from  gtd.config import get_symbols_satisfying
from multiprocessing import Pool

from gtd.style import error, paragraph, red
class Report:
    def __init__(self) -> None:
        self.elements = [] 
    
    def add(self, elem):
        self.elements.append(elem)
    
    def get_elements(self):
        return self.elements

def _extension_result_key(report):
    return report.get_elements()[0]

def is_extension(obj):
    return hasattr(obj, "__name__") and obj.__name__ == "add_extensions" and callable(obj)
def get_report(ext):
    report = Report()
    try:
        ext(report)
        return report
    except Exception as e:
        report.add(paragraph(error("Error in extension: " + str(e))))
        return report
def load_extensions() -> list:
    extension_creators = get_symbols_satisfying(is_extension)
    with Pool() as pool:
        reports = pool.map(get_report, extension_creators)
    result = []
    for report in sorted(reports, key=_extension_result_key):
        result.extend(report.get_elements())
    return result