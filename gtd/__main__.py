from typing import Dict 
from gtd.command_executor import CommandExecutor
from orgasm import command_executor_main

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

if __name__ == "__main__":
    command_executor_main(
        CommandExecutor,
        explicit_params=False
    )