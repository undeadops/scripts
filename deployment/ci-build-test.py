#!/usr/bin/env python

######
# Deployment of Dev/Test/Stage and Production Environment of
#
######
import os, sys, logging
from datetime import datetime
from keystoneclient.auth.identity import v2
from keystoneclient import session
from novaclient import client as nova_client
from pprint import pprint

# Added as workaround to openstack bug
import time


class MyDeployment:
    """
    Basic Deployment class to leverage classes
    """
    def __init__(self):
        #TODO: config file to define Image, and flavors used
        self.image_id = '67ae5eee-a75d-4e40-ae70-9cb10ae2cc0c' # ubuntu-14.04.2-20150325
        #TODO: config file to define flavor used
        self.flavor = 'm1.medium'
        #TODO: Better way of handling this...do I add in a a test to allocate a floating ip, then assign/test/release?
        self.floating_ip = '192.41.25.12'
        #TODO: Not sure on SSH keys, probably should inject these more dynamically via user scripts
        self.key_name = 'mitcha-default'
        #TODO: Yet another todo: maybe standard naming for "main network" aka "<tenant>-main"?
        self.network_id = '16011015-da6c-4769-b15f-09050ddeb72f'

        self.AUTH_URL = os.environ.get('OS_AUTH_URL')
        self.USERNAME = os.environ.get('OS_USERNAME')
        self.PASSWORD = os.environ.get('OS_PASSWORD')
        self.TENANT = os.environ.get('OS_TENANT_NAME')

        self.auth = v2.Password(auth_url=self.AUTH_URL,
                            username=self.USERNAME,
                            password=self.PASSWORD,
                            tenant_name=self.TENANT
                            )
        self.sess = session.Session(auth=self.auth)
        self.nvc = nova_client.Client('2', session=self.sess)


    def _build_webServer(self):
        """
        Build Instance for use as a webserver
        """
        dt = datetime.strftime(datetime.now(), '%Y%m%d%H%m')
        name = 'ci-webserver-%s' % dt
        fl = self.nvc.flavors.find(name=self.flavor)
        nics = [{'net-id': '%s' % self.network_id }]
        floating_ip = self.nvc.floating_ips.find(ip=self.floating_ip)

        instance = self.nvc.servers.create(name=name,
                                           image=self.image_id,
                                           flavor=fl,
                                           key_name=self.key_name,
                                           nics=nics
                                           )

        # Added as a workaround for a bug in oopenstack
        time.sleep(30)

        instance.add_floating_ip(floating_ip)

        """
        pprint(instance)
        pprint(instance.addresses)
        <Server: ci-webserver-201505121405>
        {u'GST-main': [{u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:26:41:5c',
                u'OS-EXT-IPS:type': u'fixed',
                u'addr': u'192.168.255.126',
                u'version': 4},
               {u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:26:41:5c',
                u'OS-EXT-IPS:type': u'floating',
                u'addr': u'192.41.25.12',
                u'version': 4}]}
        """



    def BuildEnvironment(self):
        """
        Build Environment to use for testing nimbus-api
        """
        webserver_id = self._build_webServer()


def main():
    """
    Main Function
    Everything begins here
    """
    try:
        os.environ['OS_AUTH_URL']
        os.environ['OS_USERNAME']
        os.environ['OS_PASSWORD']
    except:
        print "Please load Openstack Environment Variables"
        sys.exit(2)

    md = MyDeployment()
    md.BuildEnvironment()


if __name__ == "__main__":
    main()
