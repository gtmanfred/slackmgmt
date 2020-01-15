import argparse


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser('slackmgmt')
    parser.add_argument('--token', '-t', type=str, default=None)
    parser.add_argument('--debug', '-d', action='store_true')
    parser.add_argument('config', type=str)
    parser.add_argument('--events-api', '-e', action='store_true')
    return parser
