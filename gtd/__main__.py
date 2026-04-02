from typing import Dict 
from gtd.command_executor import CommandExecutor, ServicesExecutor
from orgasm import command_executor_main
from gtd.config import get_config_str
import logging 


def pretty_print(obj):
    if isinstance(obj, str):
        print(obj)
    elif isinstance(obj, list):
        for e in obj:
            pretty_print(e)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            print("%s: " % k, end="")
            pretty_print(v)
    else:
        print(obj)

def main():
    logging.basicConfig(
        level={
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG
        }[get_config_str("log_level", "INFO", "Logging level").upper()],
        format="%(levelname)s %(asctime)s %(filename)s:%(lineno)d - %(message)s",
        datefmt=r"%Y-%m-%d %H:%M:%S.%f",
        filename=get_config_str("log_file", "gtd.log", "Log file path")
    )
    command_executor_main(
        [CommandExecutor, ServicesExecutor],
        explicit_params=False
    )

if __name__ == "__main__":
    main()