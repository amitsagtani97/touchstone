import argparse
import sys
import logging
import json
import yaml

from touchstone import __version__
from . import benchmarks
from . import databases
from .utils.temp import compare_dict, mergedicts, dfs_list_dict

_logger = logging.getLogger("touchstone")


class CompareElasticData:
    def __init__(self, parser):
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
            choices=['json', 'yaml', 'csv'])
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

        self.args = parser.parse_args()

    def setup_logging(self, loglevel):
        """Setup basic logging

        Args:
          loglevel (int): minimum loglevel for emitting messages
        """
        logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
        logging.basicConfig(level=loglevel, stream=sys.stdout,
                            format=logformat, datefmt="%Y-%m-%d %H:%M:%S")

    def run(self):
        self.setup_logging(self.args.loglevel)
        print_csv = False
        truth = dict()
        metadata = "{} Key Metadata {}".format(("=" * 57), ("=" * 57))
        _logger.debug("Instantiating the benchmark instance")
        benchmark_instance = benchmarks.grab(args.benchmark,
                                             source_type=args.database,
                                             harness_type=args.harness)
        if len(self.args.conn_url) < len(self.args.uuid):
            self.args.conn_url = [self.args.conn_url[0]] * len(self.args.uuid)
        if self.args.output == "csv":
            print_csv = True
            printed_header = False
        for index in benchmark_instance.emit_indices():
            _compare_header = "{:40} |".format("key")
            compare_uuid_dict = {}
            for key in benchmark_instance.emit_compare_map()[index]:
                compare_uuid_dict[key] = {}
            for uuid_index, uuid in enumerate(self.args.uuid):
                _compare_header += " {:40} |".format(uuid)
                database_instance = \
                    databases.grab(self.args.database,
                                   conn_url=self.args.conn_url[uuid_index])
                compare_uuid_dict = \
                    database_instance.emit_compare_dict(uuid=uuid,
                                                        compare_map=benchmark_instance.emit_compare_map(),
                                                        # noqa
                                                        index=index,
                                                        input_dict=compare_uuid_dict)  # noqa
            if self.args.output in ["json", "yaml"]:
                compute_uuid_dict = {}
                for compute in benchmark_instance.emit_compute_map()[index]:
                    current_compute_dict = {}
                    compute_aggs_set = []
                    for uuid_index, uuid in enumerate(self.args.uuid):
                        database_instance = \
                            databases.grab(args.database,
                                           conn_url=self.args.conn_url[uuid_index])
                        catch = \
                            database_instance.emit_compute_dict(uuid=uuid,
                                                                compute_map=compute,  # noqa
                                                                index=index,
                                                                input_dict=compare_uuid_dict)  # noqa
                        if catch != {}:
                            current_compute_dict = \
                                dfs_list_dict(list(compute['filter'].items()),
                                              compute_uuid_dict,
                                              len(compute['filter']), catch)
                            compute_uuid_dict = \
                                dict(mergedicts(compute_uuid_dict, current_compute_dict))  # noqa
                truth = dict(mergedicts(truth, compute_uuid_dict))
            else:
                for key in benchmark_instance.emit_compare_map()[index]:
                    _message = "{:40} |".format(key)
                    for uuid in args.uuid:
                        _message += " {:40} |".format(compare_uuid_dict[key][uuid])
                    metadata += "\n{}".format(_message)
                for compute in benchmark_instance.emit_compute_map()[index]:
                    compute_uuid_dict = {}
                    compute_aggs_set = []
                    if not print_csv:
                        _compute_header = "{:30} |".format("bucket_name")
                        _compute_value = "{:30} |".format("bucket_value")
                    else:
                        _compute_header = ""
                        _compute_value = ""
                    for key, value in compute['filter'].items():
                        if not print_csv:
                            _compute_header += " {:20} |".format(key)
                            _compute_value += " {:20} |".format(value)
                        else:
                            _compute_header += "{}, ".format(key)
                            _compute_value += "{}, ".format(value)
                    for uuid_index, uuid in enumerate(self.args.uuid):
                        database_instance = \
                            databases.grab(self.args.database,
                                           conn_url=self.args.conn_url[uuid_index])
                        _current_uuid_dict = \
                            database_instance.emit_compute_dict(uuid=uuid,
                                                                compute_map=compute,
                                                                index=index,
                                                                input_dict=compare_uuid_dict)  # noqa
                        compute_aggs_set = \
                            compute_aggs_set + database_instance._aggs_list
                        compute_uuid_dict = \
                            dict(mergedicts(compute_uuid_dict, _current_uuid_dict))
                    compute_aggs_set = set(compute_aggs_set)
                    compute_buckets = database_instance._bucket_list
                    if print_csv:
                        for key in compute_buckets:
                            _compute_header += "{}, ".format(key)
                        _compute_header += "key, uuid, value"
                        if not printed_header:
                            print(_compute_header)
                            printed_header = True
                    compare_dict(compute_uuid_dict, compute_aggs_set, _compute_value,
                                 compute_buckets, self.args.uuid, _compute_header,
                                 max_level=2 * len(compute_buckets), csv=print_csv)
        if self.args.output == "json":
            print(json.dumps(truth, indent=4))
        elif self.args.output == "yaml":
            print(yaml.dump(truth, allow_unicode=True))
        elif self.args.output == "csv":
            pass
        else:
            metadata += "\n{} End Metadata {}".format(("=" * 57), ("=" * 57))
            print(metadata)
        _logger.info("Script ends here")
