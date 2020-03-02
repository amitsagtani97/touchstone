# -*- coding: utf-8 -*-
import argparse
import sys
import logging
import json
import yaml

from touchstone import __version__
from . import benchmarks
from . import databases
from .utils.temp import compare_dict, mergedicts, dfs_list_dict

__author__ = "aakarshg"
__copyright__ = "aakarshg"
__license__ = "mit"

_logger = logging.getLogger("touchstone")


def emit_csv(values,args):
    """ Present user with CSV of comparison data.
    Args:
      values ([dict]): Comparison dictionary.
      args ([argparse]) : Args passed to 

    Returns:
      :bool: True : if CSV is presented
             False: if we are unable to present results
    """
    if len(values) > 0 :
        header="Test Type, Protocol, Message Size, Threads, UUID, Key, Value"
        print(header)
    else:
        print("Error loading values")
        return False
    for test_type in values['test_type.keyword'] :
        for protocol in values['test_type.keyword'][test_type]['protocol'] :
            for message_size in values['test_type.keyword'][test_type]['protocol'
                    ][protocol]['message_size'] :
                for threads in values['test_type.keyword'][test_type]['protocol'
                        ][protocol]['message_size'][message_size]['num_threads'] :
                    for metric in values['test_type.keyword'][test_type]['protocol'
                            ][protocol]['message_size'][message_size]['num_threads'][threads] :
                        data = "{}, {}, {}, {}".format(test_type,protocol,message_size,threads)
                        for uid in args.uuid :
                            print("{}, {}, {}, {}".format(data,uid,metric,values['test_type.keyword'][test_type]
                                    ['protocol'][protocol]['message_size'][message_size]
                                    ['num_threads'][threads][metric][uid]))
    return True

def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="compare results from benchmarks")
    parser.add_argument(
        "--version",
        action="version",
        version="touchstone {ver}".format(ver=__version__))
    parser.add_argument(
        dest="benchmark",
        help="which type of benchmark to compare",
        type=str,
        choices=['uperf', 'ycsb', 'pgbench'],
        metavar="benchmark")
    parser.add_argument(
        dest="database",
        help="the type of database data is stored in",
        type=str,
        choices=['elasticsearch'],
        metavar="database")
    parser.add_argument(
        dest="harness",
        help="the test harness that was used to run the benchmark",
        type=str,
        choices=['ripsaw'],
        metavar="harness")
    parser.add_argument(
        '-u', '--uuid',
        dest="uuid",
        help="2 uuids to compare",
        type=str,
        nargs='+')
    parser.add_argument(
        '-o', '--output',
        dest="output",
        help="How should touchstone output the result",
        type=str,
        choices=['json', 'yaml','csv'])
    parser.add_argument(
        '-url', '--connection-url',
        dest="conn_url",
        help="the database connection strings in the same order as the uuids",
        type=str,
        nargs='+')
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO)
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG)
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    _logger.debug("Instantiating the benchmark instance")
    benchmark_instance = benchmarks.grab(args.benchmark,
                                         source_type=args.database,
                                         harness_type=args.harness)
    if len(args.conn_url) < len(args.uuid):
        args.conn_url = [args.conn_url[0]] * len(args.uuid)
    for index in benchmark_instance.emit_indices():
        _compare_header = "{:40} |".format("key")
        compare_uuid_dict = {}
        for key in benchmark_instance.emit_compare_map()[index]:
            compare_uuid_dict[key] = {}
        for uuid_index, uuid in enumerate(args.uuid):
            _compare_header += " {:40} |".format(uuid)
            database_instance = \
                databases.grab(args.database,
                               conn_url=args.conn_url[uuid_index])
            compare_uuid_dict = \
                database_instance.emit_compare_dict(uuid=uuid,
                                                    compare_map=benchmark_instance.emit_compare_map(), # noqa
                                                    index=index,
                                                    input_dict=compare_uuid_dict) # noqa
        if args.output:
            compute_uuid_dict = {}
            for compute in benchmark_instance.emit_compute_map()[index]:
                current_compute_dict = {}
                compute_aggs_set = []
                for uuid_index, uuid in enumerate(args.uuid):
                    database_instance = \
                        databases.grab(args.database,
                                       conn_url=args.conn_url[uuid_index])
                    catch = \
                        database_instance.emit_compute_dict(uuid=uuid,
                                                            compute_map=compute, # noqa
                                                            index=index,
                                                            input_dict=compare_uuid_dict) # noqa
                    if catch != {}:
                        current_compute_dict = \
                            dfs_list_dict(list(compute['filter'].items()),
                                          compute_uuid_dict,
                                          len(compute['filter']), catch)
                        compute_uuid_dict = \
                            dict(mergedicts(compute_uuid_dict, current_compute_dict)) # noqa
            if args.output == "json":
                print(json.dumps(compute_uuid_dict, indent=4))
            if args.output == "yaml":
                print(yaml.dump(compute_uuid_dict, allow_unicode=True))
            if args.output == "csv":
                emit_csv(compute_uuid_dict,args)
            exit(0)

        print("{} Key Metadata {}".format(("=" * 57), ("=" * 57)))
        for key in benchmark_instance.emit_compare_map()[index]:
            _message = "{:40} |".format(key)
            for uuid in args.uuid:
                _message += " {:40} |".format(compare_uuid_dict[key][uuid])
            print(_message)
        print("{} End Metadata {}".format(("=" * 57), ("=" * 57)))
        print("")
        print("")
        for compute in benchmark_instance.emit_compute_map()[index]:
            compute_uuid_dict = {}
            compute_aggs_set = []
            _compute_header = "{:30} |".format("bucket_name")
            _compute_value = "{:30} |".format("bucket_value")
            for key, value in compute['filter'].items():
                _compute_header += " {:20} |".format(key)
                _compute_value += " {:20} |".format(value)
            for uuid_index, uuid in enumerate(args.uuid):
                database_instance = \
                    databases.grab(args.database,
                                   conn_url=args.conn_url[uuid_index])
                _current_uuid_dict = \
                    database_instance.emit_compute_dict(uuid=uuid,
                                                        compute_map=compute,
                                                        index=index,
                                                        input_dict=compare_uuid_dict) # noqa
                compute_aggs_set = \
                    compute_aggs_set + database_instance._aggs_list
                compute_uuid_dict = \
                    dict(mergedicts(compute_uuid_dict, _current_uuid_dict))
            compute_aggs_set = set(compute_aggs_set)
            compute_buckets = database_instance._bucket_list
            compare_dict(compute_uuid_dict, compute_aggs_set, _compute_value,
                         compute_buckets, args.uuid, _compute_header,
                         max_level=2 * len(compute_buckets))

    _logger.info("Script ends here")


def render():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    render()
