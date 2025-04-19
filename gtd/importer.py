
from datetime import date 
from abc import ABC, abstractmethod


class Importer(ABC):

    @abstractmethod
    def create(self, 
            title: str, 
            description: str, 
            due_date: date = None,
            context: str = None,
            project: str = None,
            checklist: list[str] = None,
        ):
        """
        Create a new task with the given parameters.
        """
        pass

    @abstractmethod
    def exists(self, 
            title: str, 
            description: str = None,
            due_date: date = None,
            context: str = None,
            project: str = None,
        ) -> bool:
        """
        Check if a task with the given parameters already exists.
        """
        pass

    @abstractmethod
    def create_project(self, name: str):
        """
        Create a new project with the given name.
        """
        pass

    @abstractmethod
    def list_projects(self) -> list[str]:
        """
        List all projects.
        """
        pass

def import_task(
    importer: Importer,
    unique: bool,
    title: str, 
    description: str = None,
    due_date: date = None,
    context: str = None,
    project: str = None,
    checklist: list[str] = None,
):
    """
    Import a task with the given parameters.
    """
    if unique and importer.exists(title, description, due_date, context, project):
        print(f"Task '{title}' already exists.")
        return True

    try:
        importer.create(title, description, due_date, context, project, checklist)
    except Exception as e:
        print(f"Error creating task '{title}': {e}")
        return False
    else:
        print(f"Task '{title}' created.")
        return True