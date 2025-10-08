import logging
import os
from rich.logging import RichHandler
from rich.console import Console
import shutil
import esgvoc.core.service as service

_LOGGER = logging.getLogger(__name__)

rich_handler = RichHandler(rich_tracebacks=True)
_LOGGER.addHandler(rich_handler)


def reset_init_repo():
    service_settings = service.service_settings
    if (service_settings.universe.local_path) and os.path.exists(service_settings.universe.local_path):
        shutil.rmtree(service_settings.universe.local_path)

    for _, proj in service_settings.projects.items():
        if (proj.local_path) and os.path.exists(proj.local_path):
            shutil.rmtree(proj.local_path)
    service.state_service.get_state_summary()


def reset_init_db():
    service_settings = service.service_settings
    if (service_settings.universe.db_path) and os.path.exists(service_settings.universe.db_path):
        os.remove(service_settings.universe.db_path)
    for _, proj in service_settings.projects.items():
        if (proj.db_path) and os.path.exists(proj.db_path):
            os.remove(proj.db_path)
    service.state_service.get_state_summary()


def reset_init_all():
    reset_init_db()
    reset_init_repo()


def display(table):
    console = Console(record=True, width=200)
    console.print(table)


def install():
    service.state_service.synchronize_all()


if __name__ == "__main__":

    def Nothing():  # IT WORKS
        reset_init_all()
        display(service.state_service.table())
        service.state_service.universe.sync()
        display(service.state_service.table())
        for _, proj in service.state_service.projects.items():
            proj.sync()
        display(service.state_service.table())

    def OnlyLocal():  # IT ALSO WORKS
        reset_init_db()
        service.state_service.universe.github_access = False
        for _, proj in service.state_service.projects.items():
            proj.github_access = False
        display(service.state_service.table())

        service.state_service.universe.sync()
        display(service.state_service.table())
        for _, proj in service.state_service.projects.items():
            proj.sync()
        display(service.state_service.table())

    # TODO Some other test to do to be complete:
    # Change the settings ... for now .. let say nobody change the settings !

    OnlyLocal()
    # service.state_service.synchronize_all()
