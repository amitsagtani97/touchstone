from prometheus_api_client import PrometheusConnect


class ComparePrometheusMetric:
    def __init__(self, metric_name, start_time_list, end_time_list):
        self.metric_name = metric_name
        self.start_time_list = start_time_list
        self.end_time_list = end_time_list
        self.pc = PrometheusConnect()

    def compare_data(self):
        output = []
        for i in range(len(self.start_time_list)):
            aggregates = {}
            aggregates['metric'] = self.metric_name
            aggregates.update(
                self.get_aggregates(self.start_time_list[i], self.end_time_list[i]))
            output.append(aggregates)
        return output

    def get_aggregates(self, start_time, end_time):
        params = {
            'start': self.start_time,
            'end': self.end_time
        }
        aggregation_operations = ['sum', 'max', 'min', 'variance', 'deviation', 'average',
                                  'percentile_95']
        return self.pc.get_metric_aggregation(self.metric_name, params, aggregation_operations)
