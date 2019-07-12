#!/usr/bin/env python3

from __future__ import print_function

import redis
import sys
import time
import yaml
from prometheus_client import start_http_server
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, REGISTRY
import logging
import argparse


class RedisExporter(object):
    def __init__(self, query, redisConnections):
        self.query = query
        self.redisConnections = redisConnections

    def collect(self):
        for metric_name in self.query['metrics']:
            metric = self.query['metrics'][metric_name]
            if 'query' not in metric:
                logging.warning("skipping metric '{}' without query".format(metric_name))
                continue
            # if connection is not given for a metric, use the "first" we find (not necessarily the first in yaml file)
            conn = metric.get('connection', list(self.redisConnections)[0])
            try:
                value = self.redisConnections[conn].execute_command(metric['query'])
            except redis.RedisError as e:
                logging.error(e)
                continue

            if value is None:
                logging.debug("skipping metric '{}' as query '{}' returned nothing".format(metric_name, metric['query']))
                continue

            try:
                value = float(value)
            except TypeError:
                logging.error("metric {}: Could not convert value '{}' to float".format(metric_name, value))
                continue

            metric_type = metric.get('type', 'gauge')
            if metric_type == 'gauge':
                yield GaugeMetricFamily(
                    metric.get('name', metric_name),
                    metric.get('description', ''),
                    value=value
                )
            elif metric_type == 'counter':
                yield CounterMetricFamily(
                    metric.get('name', metric_name),
                    metric.get('description', ''),
                    value=value
                )
            else:
                logging.error("metric {}: unknown type '{}'".format(metric_name, metric_type))


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Prometheus redis exporter')
    parser.add_argument('query_file', help="YAML file containing queries")
    args = parser.parse_args()

    with open(args.query_file, 'r') as yaml_query:
        try:
            query = yaml.load(yaml_query, Loader=yaml.FullLoader)['prometheus_redis']
        except yaml.YAMLError as e:
            logging.error(e)
            sys.exit(1)

    redisConnections = {}
    for conn in query['connections']:
        connParams = query['connections'][conn]
        redisConnections[conn] = redis.Redis(
            host=connParams.get('host', 'localhost'),
            port=connParams.get('port', 6379),
            db=connParams.get('database', 0),
            password=connParams.get('password', None)
        )

    REGISTRY.register(RedisExporter(query, redisConnections))
    start_http_server(query.get('server', {}).get('port', 9118))

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
