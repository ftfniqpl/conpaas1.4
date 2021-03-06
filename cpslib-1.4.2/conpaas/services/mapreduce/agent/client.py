# -*- coding: utf-8 -*-

"""
    :copyright: (C) 2010-2013 by Contrail Consortium.
"""

import httplib, json

from conpaas.core import https 

def _check(response):
  code, body = response
  if code != httplib.OK: raise Exception('Received http response code %d' % (code))
  data = json.loads(body)
  if data['error']: raise Exception(data['error'])
  else: return data['result']

def check_agent_process(host, port):
  method = 'check_agent_process'
  return _check(https.client.jsonrpc_get(host, port, '/', method))

def startup(host, port, ip, private_ip):
  method = 'startup'
  params = {'ip': ip,
            'private_ip': private_ip}
  return _check(https.client.jsonrpc_post(host, port, '/', method, params))
