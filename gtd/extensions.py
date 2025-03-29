
from  gtd.config import * 

class Report:
    def __init__(self) -> None:
        self.elements = [] 
    
    def add(self, elem):
        self.elements.append(elem)
    
    def get_elements(self):
        return self.elements

def load_extensions() -> list:
    report = Report()
    notify_plugins("add_extensions", report)
    return report.get_elements()
