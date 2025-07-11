from typing import Dict 
from gtd.command_executor import CommandExecutor, ServicesExecutor
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

def main():
    command_executor_main(
        [CommandExecutor, ServicesExecutor],
        explicit_params=False
    )

if __name__ == "__main__":
    main()