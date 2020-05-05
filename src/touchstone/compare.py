# -*- coding: utf-8 -*-
import argparse
import sys
import logging
import json
import yaml

from touchstone import __version__
from .compare_elastic import CompareElasticData
from .compare_prom import ComparePrometheusMetric

__author__ = "aakarshg"
__copyright__ = "aakarshg"
__license__ = "mit"

_logger = logging.getLogger("touchstone")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    parser = argparse.ArgumentParser(
        description="compare results from prometheus and benchmarks on elastic")

    parser.add_argument(
        "--version",
        action="version",
        version="touchstone {ver}".format(ver=__version__))

    parser.add_argument(
        '-t', '--tool',
        help='Provide tool name',
        choices=['prom', 'elastic'])

    index_args, unknown = parser.parse_known_args()
    print(index_args)
    if index_args.tool == "prom":
        prom_compare_object = ComparePrometheusMetric(parser)
    elif index_args.tool == "elastic":
        elastic_compare_object = CompareElasticData(parser)

def render():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])

if __name__ == "__main__":
    render()
