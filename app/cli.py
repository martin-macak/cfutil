import argparse
import sys

from commands.flatten import hook_command as cmd_flatten
from commands.retain import hook_command as cmd_retain


def run(*argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')

    cmd_flatten(parser, subparsers)
    cmd_retain(parser, subparsers)

    args = parser.parse_args(argv[1:])
    args.func(args)
    ...


def main():
    run(*sys.argv)


if __name__ == '__main__':
    run(*sys.argv)
