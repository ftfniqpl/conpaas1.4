#from libcloud.compute.types import Provider
#from libcloud.compute.providers import get_driver

import time
import json
import urllib2
import xmlrpclib

from conpaas.core.node import ServiceNode

from .base import Cloud
import logging
import logging.handlers
import memcache
import traceback

IDENTITY_ADMIN_URL = ""
ADMIN_USER = ""
ADMIN_PASSWORD = ""
ADMIN_TENANT = ""
COMPUTE_URL = ""
IMAGE_URL = ""
MEMCACHED = ""

MANAGER_DEFAULT_PORT = 443
AGENT_DEFAULT_PORT = 5555

def _setlogger(logfile):
    logger = logging.getLogger()
    rh = logging.handlers.TimedRotatingFileHandler(logfile, 'D', backupCount=7)
    fm = logging.Formatter("%(asctime)s  %(filename)s[line:%(lineno)d] %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    rh.setFormatter(fm)
    logger.addHandler(rh)
    logger.setLevel(logging.NOTSET)
    return logger

logger = _setlogger(logfile="/tmp/openstack_driver.log")

class OpenStackCloud(Cloud):
    def __init__(self, cloud_name, iaas_config):
        Cloud.__init__(self, cloud_name)
        cloud_params = ['IDENTITY_URL','IDENTITY_ADMIN_URL',
                        'COMPUTE_URL','IMAGE_URL',
                        'USER','PASSWORD','TENANT',
                        'ADMIN_USER','ADMIN_PASSWORD','ADMIN_TENANT',
                        'IMAGE_ID','FLAVOR','CV_URL','MEMCACHED']

        self._check_cloud_params(iaas_config, cloud_params)
        self.cloud_name = cloud_name

        def _get(param):
            return iaas_config.get(cloud_name, param)
        self.user = _get('USER')
        self.password = _get('PASSWORD')
        self.tenant = _get('TENANT')
        self.image_id = _get('IMAGE_ID')
        self.flavor = _get('FLAVOR')
        self.cv_url = _get('CV_URL')
        self.memcached = _get('MEMCACHED')
        self.inst_type = ''

        global IDENTITY_ADMIN_URL, ADMIN_USER, ADMIN_PASSWORD, ADMIN_TENANT, COMPUTE_URL, IMAGE_URL, IDENTITY_URL, MEMCACHED

        IDENTITY_ADMIN_URL = self.identity_admin_url = _get('IDENTITY_ADMIN_URL')
        ADMIN_USER = self.admin_user = _get('ADMIN_USER')
        ADMIN_PASSWORD = self.admin_password = _get('ADMIN_PASSWORD')
        ADMIN_TENANT = self.admin_tenant = _get('ADMIN_TENANT')
        COMPUTE_URL = self.compute_url = _get('COMPUTE_URL')
        IMAGE_URL = self.image_url = _get('IMAGE_URL')
        IDENTITY_URL = self.identity_url = _get('IDENTITY_URL')
        MEMCACHED = self.memcached
        self.cpu = None
        self.mem = None
        
    def get_cloud_type(self):
        return 'openstack'

    # connect to openstack cloud
    def _connect(self):
        self.driver = OpenStackDriver(self.user, self.password, self.tenant)
        self.connected = True

    #....2015.1.9
    def set_context_template(self, cx):
        #self.cx_template = cx
        #self._context = cx.encode('hex')
        self._context = cx

    def config(self, config_params={}, context=None):
        #if context is not None:
        #    self._context = context
        if 'inst_type' in config_params:
            self.inst_type = config_params['inst_type']
        if 'cpu' in config_params:
            self.cpu = config_params['cpu']

        if 'mem' in config_params:
            self.mem = config_params['mem']

        if context:
            #self._context = context.encode('hex')
            self._context = context

    def list_vms(self):
        return self.driver.list_nodes()

    def list_instance_types(self):
        return self.inst_types

    def new_instances(self, count, name='conpaas', inst_type=None):
        if self.connected is False:
            self._connect()

        logger.error("new_instance..context..%s" % self._context)
        kwargs = {
            'name': name,
            'image_id': self.image_id,
            'flavor': self.flavor,
            'cv_url': self.cv_url,
            'memcached': self.memcached,
            'context': {'USERDATA': self._context.encode('hex')},
        }

        #logger.error("new_instance..encode_context..%s" % self._context.encode('hex'))
        server_id, public_ip, private_ip, addr = self.driver.create_node(**kwargs)
        return [ServiceNode(server_id, public_ip, private_ip, self.cloud_name, public_port=addr)]


##tony add ..2015.1.9
class OpenStackDriver(object):
    def __init__(self, username, password, tenant):
        self.server = Client(username, password, tenant)

    def create_node(self, **kwargs):
        data = {'name': kwargs['name'],
                'image_id': kwargs['image_id'],
                'flavor': kwargs['flavor']}

        result = self.server.create_server(**data)
        if not result:
            raise Exception('create server error, {0}'.format(result))
        server_id = result['server']['id']
        server_detail = self.server.get_server_detail(server_id)
        logger.error("openstackDriver..server_id..%s..server_detail..%s" % (server_id, server_detail))

        time_counter = 0
        while 1:
            if server_detail['server']['status'] != 'ACTIVE':
                if  time_counter >=500:
                    raise Exception('vm is not running')
                server_detail = self.server.get_server_detail(server_id)
                time.sleep(5)
                continue
            break
        private_ip, addr = self._parse_ip_from_server_detail(server_id)
        logger.error("openstack..run vm private_ip:%s...addr:%s....server_id:%s" % (private_ip, addr, server_id))
        public_ip = private_ip
        #public_ip = addr
        
        context = kwargs['context']
        context['IP_PUBLIC'] = public_ip
        context['HOSTNAME'] = 'conpaas'
        
        try:
            s = xmlrpclib.ServerProxy(kwargs['cv_url'])
            result = s.saveContext('', addr, context)
            logger.info("send cv data success...server_id:%s..private_ip:%s...addr:%s...result:%s" % (server_id, private_ip, addr, result))
        except:
            logger.error("send cv error...server_id:%s...public_ip:%s...reason:%s" % (server_id, public_ip, traceback.format_exc()))
        return server_id, public_ip, private_ip ,addr

    def list_nodes(self):
        node_list = []
        res = self.server.list_servers()
        for server in res['servers']:
            server_id = server['id']
            private_ip, addr = self._parse_ip_from_server_detail(server_id)
            node_list.append(ServiceNode(server_id, private_ip, private_ip, 'iaas', public_port=addr))
        return node_list
       
    def destroy_node(self, server_node):
        return self.server.delete_server(server_node.id)

    def _parse_ip_from_server_detail(self, server_id):
        private_ip = None
        addr = None
        try:
            mc = memcache.Client([MEMCACHED])
            server_info = mc.get(str(server_id))
            logger.error("from memcache get server_info..memcache:%s...server_id:%s...server_info:%s" % (MEMCACHED, server_id, server_info))
            private_ip = server_info['private_ip']
            ports = server_info['port']
            for p in ports.split(','):
                src_port, des_port = p.split('/')
                #if int(src_port) == MANAGER_DEFAULT_PORT:
                if int(src_port) in (MANAGER_DEFAULT_PORT, AGENT_DEFAULT_PORT):
                    addr = '{0}:{1}'.format(server_info['host'], des_port)
                    break
        except:
            logger.error("parse_ip from server_detail error:%s....%s"% (server_id, traceback.format_exc()))
        return private_ip, addr
        

##tony add ..2015.1.9
class Client(object):
    def __init__(self, user, password, tenant):
        self._token = _get_token(user, password, tenant)
        self.tenant_id = self._get_tenant_id(tenant)

    def _get_tenant_id(self, tenant_name):
        tenants = list_tenants()
        for tenant in tenants['tenants']:
            if tenant['name'] == tenant_name:
                return tenant['id']

    def list_images(self):
        headers = {'User-Agent': 'python-keystoneclient', 'X-Auth-Token': self._token}
        url = "{0}/images".format(IMAGE_URL)
        return _http_request(url, headers=headers)

    def list_servers(self):
        headers = {"User-Agent":"python-keystoneclient", "X-Auth-Token":self._token}
        url = "{0}/{1}/servers".format(COMPUTE_URL, self.tenant_id)
        return _http_request(url,headers=headers)

    def create_server(self,**params):
        name = params.get('name')
        image_id = params.get('image_id')
        flavor = params.get('flavor')

        data = {
            "server":{
                "name":name,
                "imageRef":image_id,
                "flavorRef":flavor,
                "max_count":1,
                "min_count":1,
                "security_groups":[{"name":"default"}]
             }
         }

        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent":"python-keystoneclient",
                   "X-Auth-Token":self._token}
        url = "{0}/{1}/servers".format(COMPUTE_URL, self.tenant_id)
        return _http_request(url,headers=headers,data=data)

    def get_server_detail(self,server_id):
        headers = {"User-Agent":"python-keystoneclient", "X-Auth-Token":self._token}

        url = "{0}/{1}/servers/{2}".format(COMPUTE_URL, self.tenant_id, server_id)
        return _http_request(url,headers=headers)

    def delete_server(self,server_id):
        headers = {"User-Agent":"python-keystoneclient", "X-Auth-Token":self._token}
        url = "{0}/{1}/servers/{2}".format(COMPUTE_URL, self.tenant_id, server_id)
        return _http_request(url,headers=headers,method='DELETE')

def _http_request(url,headers='',data='',method=None):
    req = urllib2.Request(url)
    if headers and isinstance(headers,dict):
        for key,val in headers.items():
            req.add_header(key, val)
    if data:
        data = json.dumps(data)
        req.add_data(data)

    #method may be 'PUT' or 'DELETE'
    if method:
        req.get_method = lambda: method

    res = None
    #request to url
    try:
        res = urllib2.urlopen(req,timeout=120)
    except :
        traceback.print_exc()

    if res:
        try:
            _data = res.read()
            #Log.debug("OpenStack server reponse :%s"%_data)
            return json.loads(_data)
        except :
            return _data

    return res

def _get_token(username,password,tenant=''):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = {"auth": {
                "tenantName": tenant, 
                "passwordCredentials": {
                    "username": username,
                    "password": password
                    }
                }
            }

    url = "{0}/tokens".format(IDENTITY_URL)
    res = _http_request(url,headers=headers,data=data)
    return res['access']['token']['id']

def admin_token():
    return _get_token(ADMIN_USER,ADMIN_PASSWORD,ADMIN_TENANT)

def list_tenants():
    headers = {"User-Agent":"python-keystoneclient", "X-Auth-Token":admin_token()}
    url = "{0}/tenants".format(IDENTITY_ADMIN_URL)
    return _http_request(url,headers=headers)

def list_endpoints():
    headers = {"User-Agent": "python-keystoneclient", "X-Auth-Token":admin_token()}
    url = "{0}/endpoints".format(IDENTITY_ADMIN_URL)
    return _http_request(url,headers=headers)
