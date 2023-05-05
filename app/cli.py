import argparse
import sys


def run(*argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_flatten = subparsers.add_parser('flatten', help='flatten help')
    parser_flatten.add_argument('template', type=str, help='template file')

    args = parser.parse_args(argv[1:])


def main():
    run(*sys.argv)


if __name__ == '__main__':
    run(*sys.argv)
