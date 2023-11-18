import argparse
from typing import Dict 
from gtd.command_executor import CommandExecutor
from gtd.command_class_inspection import * 


def pretty_print(obj):
    if isinstance(obj, str):
        print(obj)
    elif isinstance(obj, list):
        for e in obj:
            pretty_print(e)
    elif isinstance(obj, dict):
        import json 
        print(json.dumps(obj, indent=4, sort_keys=True))
    else:
        print(obj)

parser = argparse.ArgumentParser()

available_commands = get_available_commands(CommandExecutor)

command_parsers = parser.add_subparsers(dest="command")


commands: Dict[str, argparse.ArgumentParser] = {}
for command in available_commands:
    commands[command] = command_parsers.add_parser(command)

    for arg in get_arguments(getattr(CommandExecutor, command)):
        commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
            required=True, 
            action="store", 
            type=get_arg_type(getattr(CommandExecutor, command), arg),
            help=get_arg_description(getattr(CommandExecutor, command), arg)
        )
    for arg, value in get_optional_arguments(getattr(CommandExecutor, command)):
        if get_arg_type(getattr(CommandExecutor, command), arg) == bool:
                commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
                default=value,
                action="store_const",
                const=True,
                help=get_arg_description(getattr(CommandExecutor, command), arg)
            )
        else:
            commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
                default=value,
                action="store",
                type=get_arg_type(getattr(CommandExecutor, command), arg),
                help=get_arg_description(getattr(CommandExecutor, command), arg)
            )


args, _ = parser.parse_known_args()
def main():
    executor = CommandExecutor()
    if hasattr(executor, args.command):
        m = getattr(executor, args.command)
        A = {}
        for arg in get_arguments(m):
            if arg != "self":
                A[arg] = getattr(args, arg)
        for arg, _ in get_optional_arguments(m):
            A[arg] = getattr(args, arg)
        view = m(**A)
        pretty_print(view)
    else:
        print("This feature is not implemented yet")

if __name__ == "__main__":
    main()