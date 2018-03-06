import sys
import time
import json
import requests
import time
import logging
import os
from pprint import pprint
import ConfigParser
from prometheus_client.parser import text_string_to_metric_families
from prometheus_client import Summary, core, exposition
# import uptime


LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
LOG.setLevel(logging.DEBUG)


class configuration(object):
    def __init__(self, file):
        self.Config = ConfigParser.ConfigParser()
        self.Config.read(file)

    def ConfigSectionMap(self,section):
        dict1 = {}
        options = self.Config.options(section)
        for option in options:
            try:
                dict1[option] = self.Config.get(section, option)
                if dict1[option] == -1:
                    DebugPrint("skip: %s" % option)
            except:
                print("exception on %s!" % option)
                dict1[option] = None
        return dict1


def build_metric(name, documentation, typ, samples):
    metric = core.Metric(name, documentation, typ)
    metric.samples = samples
    return metric


def generate_latest(families):
    '''Returns the metrics from the registry in latest text format as a string.'''
    output = []
    for metric in families:
        output.append('# HELP {0} {1}'.format(
            metric.name, metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
        output.append('\n# TYPE {0} {1}\n'.format(metric.name, metric.type))
        for name, labels, (value, stamp) in metric.samples:
            if labels:
                labelstr = '{{{0}}}'.format(','.join(
                    ['{0}="{1}"'.format(
                     k, v.replace('\\', r'\\').replace('\n', r'\n').replace('"', r'\"'))
                     for k, v in sorted(labels.items())]))
            else:
                labelstr = ''
            output.append('{0}{1}{2} {3}\n'.format(name, labelstr, core._floatToGoString(value), stamp))
    return ''.join(output).encode('utf-8')


def get_metadata():
    raw = requests.get("http://169.254.169.254/openstack/latest/meta_data.json") 
    return raw.json()


def print_raw_metrics(metrics):
    for family in text_string_to_metric_families(metrics):
        for sample in family.samples:
            print("Name: {2} Labels: {3} Value: {4} ({0}, {1})".format(family.name, family.type, *sample))

to_translate = {
    'cpu_usage_active': {
        'new_name': 'vm_cpu_perc',
        'new_keys': {
            'cpu': 'core'
        }
    },
    'mem_available_percent': {
        'new_name': 'vm_mem_perc',
        'new_keys': {}
    },
    'mem_free': {
        'new_name': 'vm_mem_free_MB',
        'new_keys': {},
        'div': 1024.0
    },
    'mem_total': {
        'new_name': 'vm_mem_total_MB',
        'new_keys': {},
        'div': 1024.0
    },
    'net_bytes_recv': {
        'new_name': 'vm_net_rx_MB',
        'new_keys': {
            'interface': 'inf'
        },
        'div': 1024.0**2
    },
    'net_bytes_sent': {
        'new_name': 'vm_net_tx_MB',
        'new_keys': {
            'interface': 'inf'
        },
        'div': 1024.0**2
    },
    'disk_used_percent': {
        'new_name': 'vm_disk_usage_perc',
        'new_keys': {
            'device': 'file_system'
        }
    },
    'disk_used': {
        'new_name': 'vm_disk_used_1k_blocks',
        'new_keys': {
            'device': 'file_system'
        },
        'div': 1024.0
    },
    'disk_total': {
        'new_name': 'vm_disk_total_1k_blocks',
        'new_keys': {
            'device': 'file_system'
        },
        'div': 1024.0
    },
    'system_uptime': {
        'new_name': 'vm_up',
        'new_keys': {}
    },
    'net_packets_recv': {
        'new_name': 'vm_net_rx_pps',
        'new_keys': {
            'interface': 'inf'
        }
    },
    'net_packets_sent': {
        'new_name': 'vm_net_tx_pps',
        'new_keys': {
            'interface': 'inf'
        }
    },
    'net_bytes_recv': {
        'new_name': 'vm_net_rx_bps',
        'new_keys': {
            'interface': 'inf'
        }
    },
    'net_bytes_sent': {
        'new_name': 'vm_net_tx_bps',
        'new_keys': {
            'interface': 'inf'
        }
    },

}

def translate_metrics(metrics, now, id_):
    new_families = []
    to_keep = ["vm_net_rx_pps", "vm_net_tx_pps", "vm_net_rx_bps", "vm_net_tx_bps"]
    has_mem_perc_metric = False
    reprocess = {}
    for elt in to_keep:
        reprocess[elt] = {}
    for family in text_string_to_metric_families(metrics):
        samples = []
        conf = to_translate.get(family.name)
        if conf:
            samples = []
            for sample in family.samples:
                labels = {}
                for key, new_key in conf['new_keys'].iteritems():
                    labels[new_key] = sample[1][key]
                labels['id'] = id_
                new_value = sample[2]
                d = conf.get('div', None)
                if d:
                    new_value = new_value / d
                samples.append((conf['new_name'], labels, (new_value, now)))
            m = build_metric(conf['new_name'], family.documentation, "gauge", samples)  # conf.get('new_type', family.type)
            if m.name in to_keep:
                for (_, labels, data) in samples:
                    reprocess[m.name][labels['inf']] = data[0]
            else:
                new_families.append(m)
            if m.name == 'vm_mem_perc':
                has_mem_perc_metric = True
    if not has_mem_perc_metric:
        m = build_metric("vm_mem_perc", "", "gauge", [("vm_mem_perc", {'id': id_}, (time.time() % 6, now))])
        new_families.append(m)
    return (new_families, reprocess)


# def add_uptime(metrics, now, id_):
#     m = build_metric('vm_up', "", "gauge", [('vm_up', {'id': id_}, (uptime.uptime(), now))])
#     metrics.append(m)


def handle_reprocess(metrics, old_now, oldest, late_now, latest, id_):
    delta = (late_now - old_now) / 1000.0
    for family_name, delt in latest.iteritems():
        some_metrics = []
        for inf, data in delt.iteritems():
            try:
                old_data = oldest[family_name][inf]
                mean = (data - old_data) / delta
                some_metrics.append((family_name, {'id': id_, 'inf': inf}, (mean, late_now)))
            except KeyError:
                pass
        m = build_metric(family_name, "", "gauge", some_metrics)
        metrics.append(m)
    return metrics


def post_metrics(node_ ,type_, data_, server_):
    url = server_+"/job/"+type_+"/instance/"+node_
    headers = {'Content-Type': 'text/html'}
    try:
        r = requests.put(url, data=data_, headers=headers, timeout=10.0)
        LOG.debug("Post metrics response: %s", r.text)
    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
        LOG.error("Error while posting metrics: %s", e)


def main__():
    id_ = 'tor-vnf'
    LOG.info("Starting")
    meta = get_metadata()
    port = sys.argv[1] if len(sys.argv) > 1 else '9100'
    now_0 = int(time.time()) * 1000
    metrics = requests.get("http://localhost:{}/metrics".format(port)).content
    print_raw_metrics(metrics)
    print("\n\n________________ \n\n")
    new_families, to_reprocess_0 = translate_metrics(metrics, now_0, id_)
    time.sleep(5)
    now_1 = int(time.time()) * 1000
    metrics = requests.get("http://localhost:{}/metrics".format(port)).content
    new_families, to_reprocess_1 = translate_metrics(metrics, now_1, id_)
    handle_reprocess(new_families, now_0, to_reprocess_0, now_1, to_reprocess_1, id_)
    a = generate_latest(new_families)
    print(a)
    pprint((now_0, to_reprocess_0))
    pprint((now_1, to_reprocess_1))
    post_metrics("vtc", "vnf", a, "http://10.30.0.112:9091/metrics")


def main():
    LOG.info("Starting")
    #read configuration
    interval=3.0
    conf = configuration("/opt/Monitoring/node.conf")
    node_name = os.getenv('NODE_NAME', conf.ConfigSectionMap("vm_node")['node_name'])
    prometh_server = os.getenv('PROM_SRV', conf.ConfigSectionMap("Prometheus")['server_url'])
    interval = float(conf.ConfigSectionMap("vm_node")['post_freq'])
    meta = get_metadata()
    vm_id = meta['uuid']
    node_name +=":"+vm_id
    LOG.info("interval=%d; node_name=%s; prometh_server=%s; vm_id=%s", interval, node_name, prometh_server, vm_id)
    port = 9100
    now_0 = int(time.time()) * 1000
    metrics = requests.get("http://localhost:{}/metrics".format(port)).content
    new_families, to_reprocess_0 = translate_metrics(metrics, now_0, vm_id)
    LOG.info("Got first metrics")
    while True:
        time.sleep(interval)
        now_1 = int(time.time()) * 1000
        metrics = requests.get("http://localhost:{}/metrics".format(port)).content
        new_families, to_reprocess_1 = translate_metrics(metrics, now_1, vm_id)
        handle_reprocess(new_families, now_0, to_reprocess_0, now_1, to_reprocess_1, vm_id)
        a = generate_latest(new_families)
        print(a)
        print("\n")
        post_metrics(node_name, "vnf", a, prometh_server)
        now_0 = now_1
        to_reprocess_0 = to_reprocess_1


if __name__ == "__main__":
    main()








