'''
Created on Jun 13, 2017

@author: ubuntu
'''

import logging
import yaml
import json
import time
import os
import datetime
import docker
import requests
from sonmanobase import messaging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
logging.getLogger("son-mano-base:messaging").setLevel(logging.INFO)


class fakeflm(object):
    def __init__(self):

        self.name = 'fake-flm'
        self.version = '0.1-dev'
        self.description = 'description'
        self.client = docker.from_env() # docker.DockerClient(base_url='unix://var/run/docker.sock')

        LOG.info("Start sending VNFR in cwd={}".format(os.getcwd()))

        # create and initialize broker connection
        self.manoconn = messaging.ManoBrokerRequestResponseConnection(self.name)

        self.manoconn.subscribe(self._on_publish,'son.configuration')

        self.end = False

        self.publish_nsd()
        
        self._run()

    def _run(self):
        # go into infinity loop
        while self.end == False:
            # LOG.info("_run, sleeping")
            time.sleep(1)

    def _publish_cnt(self, cnt):
        # ['VNFR'][x]['virtual_deployment_units'][0]['vm_image']
        # ['VNFR'][x]['virtual_deployment_units'][0]['vnfc_instance'][0]['connection_points'][0]['type']['address']
        for i in range(12):
            LOG.debug('Querying the son-emu rest api #%s', i)
            req = requests.get('http://172.17.0.1:5001/restapi/compute/{}/{}'.format('dc1', cnt.name[3:])) # remove 'mn.'
            try:
                req.raise_for_status()
                topo = json.loads(req.text)
            except Exception as exc:
                LOG.warning('Exception when looking for the VDU interfaces of cnt %s,  %s, %s', cnt.name, type(exc), exc)
                topo = None
                time.sleep(1)
                continue
            break
        if not topo:
            LOG.error('Unable to publish cnt %s', cnt.name)
            return
        cps = []
        for elt in topo['network']:
            interface = {'hardware_address': elt['mac'], 'address': elt['ip']}
            if elt['netmask'] == '24':
                _type = 'management'
            else:
                _type = 'internal'
                interface['netmask'] = '???'
            cps.append({'type': _type, 'id': elt['intf_name'], 'interface': interface})
        vdu = {'vc_id': cnt.id, 'connection_points': cps}
        message = {'VNFR': [{'virtual_deployment_units': [{'vm_image': cnt.image.tags[0], 'vnfc_instance': [vdu]}]}], '_in_sonemulator': ''}
        self.manoconn.publish('son.configuration.1.v1', json.dumps(message))

    def _is_emulator_infra(self, cnt):
        return cnt.name == 'cadvisor' or cnt.name == 'pushgateway'

    def publish_nsd(self):
        LOG.info('Detecting already running VNF in son-emu')
        now = datetime.datetime.utcnow()
        already_seen_cnt = []
        for acnt in self.client.containers.list(filters={'status': 'running', 'label': 'com.containernet'}):
            if self._is_emulator_infra(acnt):
                LOG.debug('Ignoring infra container %s', acnt.name)
                continue
            LOG.debug('Detected the running VNF %s', acnt.name)
            self._publish_cnt(acnt)
            already_seen_cnt.append(acnt.id)
        LOG.debug('Waiting for Docker events')
        for event in self.client.events(since=now, decode=True):
            # {"status":"start","id":"ff3136c0170261794bc5e8dcbc7bd331a462cb23bd7fbf4fe91f9e1a7e52ca61","from":"ubuntu","Type":"container","Action":"start","Actor":{"ID":"ff3136c0170261794bc5e8dcbc7bd331a462cb23bd7fbf4fe91f9e1a7e52ca61","Attributes":{"image":"ubuntu","name":"zealous_bell"}},"scope":"local","time":1504792794,"timeNano":1504792794950767976}
            if event.get('status') == 'start':
                LOG.debug('Docker start event %s', event)
                cnt = self.client.containers.get(event['id'])
                if (not 'com.containernet' in cnt.labels) or (cnt.id in already_seen_cnt) or (self._is_emulator_infra(cnt)):
                    LOG.debug('Ignoring container %s', cnt.id)
                    continue
                self._publish_cnt(cnt)
        self.end = True

    def _on_publish(self, ch, method, props, response):
        if props.app_id != self.name:
            response = yaml.load(response)
            if type(response) == dict:
                try:
                    LOG.info('Ack my publish %s', response)
                except BaseException as error:
                    LOG.error('Error when ack my publish %s', error)


def main():
    fakeflm()


if __name__ == '__main__':
    main()
