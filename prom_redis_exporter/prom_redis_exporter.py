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


def create_logger(level=logging.INFO):
    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('[%(levelname)s] [%(created)f] [%(module)s]: %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    return logger

logger = create_logger()


class RedisExporter():
    def __init__(self, metrics, redisConnections):
        self.metrics = metrics
        self.redisConnections = redisConnections

    def collect(self):
        for metric_name in self.metrics:
            metric = self.metrics[metric_name]

            if 'query' not in metric and 'queries' not in metric:
                logger.warning("skipping metric '{}' without queries".format(metric_name))
                continue

            metric_type = metric.get('type', 'gauge')
            if metric_type == 'gauge':
                MetricFamily = GaugeMetricFamily
            elif metric_type == 'counter':
                MetricFamily = CounterMetricFamily
            else:
                logger.error("metric {}: unknown type '{}'".format(metric_name, metric_type))
                continue

            labels = metric.get('labels', None)
            if labels is not None and not isinstance(labels, list):
                logger.warning("skipping metric '{}': 'labels' is not a list".format(metric_name))
                continue

            queries = metric.get('queries', None)
            if queries is None:
                # support old single 'query' without labels
                queries = [{'label_values': [], 'query': metric.get('query')}]
            elif not isinstance(queries, list):
                logger.warning("skipping metric '{}': 'queries' is not a list".format(metric_name))
                continue
            elif len(queries) == 0:
                logger.warning("skipping metric '{}' without any queries".format(metric_name))
                continue

            # if connection is not given for a metric, use the "first" we find (not necessarily the first in yaml file)
            conn = metric.get('connection', list(self.redisConnections)[0])

            def get_value(query):
                if query is None:
                    return None
                value = None
                try:
                    value = self.redisConnections[conn].execute_command(query)
                except redis.RedisError as e:
                    logger.error(e)
                    return None
                if value is None:
                    logger.debug("skipping metric '{}' as query '{}' returned nothing".format(metric_name, query))
                    return None
                try:
                    value = float(value)
                except TypeError:
                    logger.error("metric {}: query '{}': Could not convert value '{}' to float".format(metric_name, query, value))
                return value

            m = MetricFamily(
                    metric.get('name', metric_name),
                    metric.get('description', ''),
                    labels=labels)

            #logger.debug("metric {}: queries: {}".format(metric_name, queries))
            for q in queries:
                value = get_value(q.get('query'))
                if value is None:
                    continue
                label_values = q.get('label_values', [])
                if not isinstance(label_values, list):
                    label_values = [label_values]
                # ensure label values are strings
                label_values = [str(l) for l in label_values]
                m.add_metric(label_values, value)
            if m.samples:
                yield m


def main():
    parser = argparse.ArgumentParser(description='Prometheus redis exporter')
    parser.add_argument('query_file', help="YAML file containing queries")
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose logging (debug level)")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    with open(args.query_file, 'r') as yaml_query:
        try:
            query = yaml.load(yaml_query, Loader=yaml.FullLoader)['prometheus_redis']
        except yaml.YAMLError as e:
            logger.error(e)
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

    REGISTRY.register(RedisExporter(query.get('metrics', {}), redisConnections))
    port = query.get('server', {}).get('port', 9118)
    start_http_server(port)

    logger.info("Started server on port {}".format(port))

    while True:
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("shutting down")


if __name__ == "__main__":
    main()
