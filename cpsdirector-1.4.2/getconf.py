#!/usr/bin/env python

from string import Template
import readline

def rlinput(prompt, prefill=''):                                                                                                                                          
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return raw_input(prompt)
    finally:
        readline.set_startup_hook()

print 'Please note that currently only supports the installation of openstack Havana' 
host_ip = rlinput('Please enter the current host of external ip:', '192.168.18.115')
openstack_ip = rlinput('Please enter the ip address of openstack:', '192.168.18.114')

openstack_adminuser = rlinput('Please enter the admin username of openstack:', 'admin')
openstack_adminpasswd = rlinput('Please enter the admin password of openstack:', 'powerall')
openstack_admintenant = rlinput('Please enter the admin tenant name of openstack:', 'admin')

openstack_imageid = rlinput('Please enter openstack in preparation for the docker image:', '76a2804e-3adf-4b1b-8f98-131ceda0fb86')
openstack_flavorid = rlinput('Please enter openstack in preparation for the docker flavor:', '64a95788-151d-46c8-926b-5e83f75a02c3')

f = open('director.cfg.template', 'r')
c = f.read()
f.close()

t = Template(c)
d = {'HOSTIP': host_ip, 
     'OPENSTACK_IP': openstack_ip,
     'OPENSTACK_USER': openstack_adminuser,
     'OPENSTACK_PASSWORD': openstack_adminpasswd,
     'OPENSTACK_TENANT': openstack_admintenant,
     'OPENSTACK_IMAGEID': openstack_imageid,
     'OPENSTACK_FLAVORID': openstack_flavorid,
    }
strs = t.safe_substitute(d)
with open('director.cfg.example', 'w') as f:
    f.write(strs)

