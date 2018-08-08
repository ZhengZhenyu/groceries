import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import timeutils
from oslo_utils import uuidutils

from nova.tests.unit.objects import test_instance_info_cache
from nova.objects import base as obj_base
from nova import objects
from nova.objects import fields
from nova import context as nova_context
from nova.db.sqlalchemy import api_models
from nova.db.sqlalchemy import models

cfg.CONF.unregister_opts([cfg.HostAddressOpt('host'),
                          cfg.StrOpt('state_path')])


placement_opts = [
    cfg.StrOpt('region_name'),
    cfg.StrOpt('endpoint_type'),
]

cfg.CONF.unregister_opts(placement_opts, group='placement')

from neutron.objects import ports
from neutron.tests import tools
from neutron.db import models_v2
from neutron_lib import context as neutron_context

parser = argparse.ArgumentParser(
    description='The Launchpad Bug Tracker: '
                'This script can be used to track bugs registered in'
                'launchpad.net.')


parser.add_argument('--project_id', metavar='<project_id>',
                    dest='project_id', required=True,
                    help='Project ID')
parser.add_argument('--user_id', metavar='<user_id>',
                    dest='user_id', required=True,
                    help='User ID')
parser.add_argument('--db_conn', metavar='<db_conn>',
                    dest='db_conn', required=True,
                    help='DB Connection')
parser.add_argument('--cell_id', metavar='<cell_id>',
                    dest='cell_id', required=True,
                    help='Cell ID')
parser.add_argument('--trade_off', metavar='<trade_off>',
                    dest='trade_off', required=True,
                    help='Trade off prefix',
                    default='0')
parser.add_argument('--runtime', metavar='<runtime>',
                    dest='runtime', required=True,
                    help='runtime',
                    default='1')


#nova_database_connect = 'mysql+pymysql://root:root@127.0.0.1/nova_cell0?charset=utf8'
api_database_connect = 'mysql+pymysql://root:root@127.0.0.1/nova_api?charset=utf8'
neutron_database_connect = 'mysql+pymysql://root:root@127.0.0.1/neutron?charset=utf8'


def _get_fake_cache(ip=None):
    def _ip(ip, fixed=True, floats=None):
        ip_dict = {'address': ip, 'type': 'fixed'}
        if not fixed:
            ip_dict['type'] = 'floating'
        if fixed and floats:
            ip_dict['floating_ips'] = [_ip(f, fixed=False) for f in floats]
        return ip_dict

    info = [{'address': 'aa:bb:cc:dd:ee:ff',
             'id': 'fake',
             'network': {'bridge': 'br0',
                         'id': 1,
                         'label': 'private',
                         'subnets': [{'cidr': '192.168.0.0/24',
                                      'ips': [_ip(ip)]}]}}]

    return jsonutils.dumps(info)


def get_instances_with_cached_ips(project_id='fake', user_id='fake'):
    """Kludge the cache into instance(s) without having to create DB
    entries
    """
    user_id = user_id
    project_id = project_id
    no_context = nova_context.RequestContext(
        user_id, project_id, is_admin=True)
    ne_context = neutron_context.Context(user_id, project_id, is_admin=True)

    def _info_cache_for(instance, ip):
        info_cache = dict(test_instance_info_cache.fake_info_cache,
                          network_info=_get_fake_cache(ip),
                          instance_uuid=instance['uuid'])
        if isinstance(instance, obj_base.NovaObject):
            _info_cache = objects.InstanceInfoCache(no_context)
            objects.InstanceInfoCache._from_db_object(no_context, _info_cache,
                                                      info_cache)
            info_cache = _info_cache
        instance['info_cache'] = info_cache

    instances = []
    ports = []

    tradeoff = int(parsed_args.trade_off) * 4

    runtime = int(parsed_args.runtime)

    for i in xrange(1, runtime):
        for j in xrange(0 + tradeoff, 4 + tradeoff):
            ip_str = '192.168.' + str(j) + '.'
            for i in xrange(1, 250):
                ip = ip_str + str(i)
                name_str = 'perfomance_test_' + str(i)
                updates = {'id': i + 250 * j, 'name': name_str,
                           'project_id': project_id, 'user_id': user_id}
                instance = fake_instance_obj(no_context, **updates)
                _info_cache_for(instance, ip)
                instances.append(instance)
                port = _create_port(ne_context, instance.uuid, ip_address=ip)
                ports.append(port)

    return instances, ports


def fake_instance_obj(context, obj_instance_class=None, **updates):
    if obj_instance_class is None:
        obj_instance_class = objects.Instance
    expected_attrs = updates.pop('expected_attrs', None)
    flavor = updates.pop('flavor', None)
    if not flavor:
        flavor = objects.Flavor(id=1, name='flavor1',
                                memory_mb=256, vcpus=1,
                                root_gb=1, ephemeral_gb=1,
                                flavorid='1',
                                swap=0, rxtx_factor=1.0,
                                vcpu_weight=1,
                                disabled=False,
                                is_public=True,
                                extra_specs={},
                                projects=[])
        flavor.obj_reset_changes()
    inst = obj_instance_class._from_db_object(context,
               obj_instance_class(), fake_db_instance(**updates),
               expected_attrs=expected_attrs)
    inst.keypairs = objects.KeyPairList(objects=[])
    inst.tags = objects.TagList()
    if flavor:
        inst.flavor = flavor
        # This is needed for instance quota counting until we have the
        # ability to count allocations in placement.
        if 'vcpus' in flavor and 'vcpus' not in updates:
            inst.vcpus = flavor.vcpus
        if 'memory_mb' in flavor and 'memory_mb' not in updates:
            inst.memory_mb = flavor.memory_mb
    inst.old_flavor = None
    inst.new_flavor = None
    inst.obj_reset_changes()
    return inst


def fake_db_instance(**updates):
    if 'instance_type' in updates:
        if isinstance(updates['instance_type'], objects.Flavor):
            flavor = updates['instance_type']
        else:
            flavor = objects.Flavor(**updates['instance_type'])
        flavorinfo = jsonutils.dumps({
            'cur': flavor.obj_to_primitive(),
            'old': None,
            'new': None,
        })
    else:
        flavorinfo = None
    db_instance = {
        #'id': updates['id'],
        'deleted': False,
        'uuid': uuidutils.generate_uuid(),
        'user_id': updates['user_id'],
        'project_id': updates['project_id'],
        'host': 'fake-host',
        'created_at': timeutils.utcnow(),
        'pci_devices': [],
        'security_groups': [],
        'metadata': {},
        'system_metadata': {},
        'root_gb': 0,
        'ephemeral_gb': 0,
        'extra': {'pci_requests': None,
                  'flavor': flavorinfo,
                  'numa_topology': None,
                  'vcpu_model': None,
                  'device_metadata': None,
                 },
        'tags': [],
        'services': []
        }

    for name, field in objects.Instance.fields.items():
        if name in db_instance:
            continue
        if field.nullable:
            db_instance[name] = None
        elif field.default != fields.UnspecifiedDefault:
            db_instance[name] = field.default
        elif name in ['flavor', 'ec2_ids', 'keypairs', 'id']:
            pass
        else:
            raise Exception('fake_db_instance needs help with %s' % name)

    if updates:
        db_instance.update(updates)

    if db_instance.get('security_groups'):
        db_instance['security_groups'] = fake_db_secgroups(
            db_instance, db_instance['security_groups'])

    return db_instance


def fake_db_secgroups(instance, names):
    secgroups = []
    for i, name in enumerate(names):
        group_name = 'secgroup-%i' % i
        if isinstance(name, dict) and name.get('name'):
            group_name = name.get('name')
        secgroups.append(
            {'id': i,
             'instance_uuid': instance['uuid'],
             'name': group_name,
             'description': 'Fake secgroup',
             'user_id': instance['user_id'],
             'project_id': instance['project_id'],
             'deleted': False,
             'deleted_at': None,
             'created_at': timeutils.utcnow(),
             'updated_at': None,
             })
    return secgroups

def _create_port(context, device_id, ip_address):
    network_id = 'd339eb89-3b7c-4a29-8c02-83ed329ea6d5'
    subnet_id = '1f9206e1-0872-4bc1-a600-3efed860ee64'
    fixed_ips = {
        'subnet_id': subnet_id,
        'network_id': network_id,
        'ip_address': ip_address}
    ip_allocation = ports.IPAllocation(context, **fixed_ips)
    port_attrs = {
        'network_id': network_id,
        'fixed_ips': [ip_allocation]
    }
    attrs = {'project_id': context.project_id,
             'admin_state_up': True,
             'status': 'ACTIVE',
             'device_id': device_id,
             'device_owner': 'compute:nova',
             'mac_address': tools.get_random_EUI()}
    attrs.update(**port_attrs)
    port = ports.Port(context, **attrs)
    return port


def write_nova_db(Session, inst_obj):
    session = Session()
    values = dict(inst_obj)
    instance_model = models.Instance
    instance_ref = instance_model()
    instance_ref['info_cache'] = models.InstanceInfoCache()
    values['info_cache'] = {
        'network_info': values['info_cache'].network_info.json()
    }
    info_cache = values.pop('info_cache', None)
    instance_ref['info_cache'].update(info_cache)
    instance_ref['extra'] = models.InstanceExtra()
    values['extra'] = {}
    flavor = values.pop('flavor', None)
    flavor_info = {
        'cur': flavor.obj_to_primitive(),
        'old': None,
        'new': None,
    }
    objects.instance.Instance._nullify_flavor_description(flavor_info)
    values['extra']['flavor'] = jsonutils.dumps(flavor_info)
    extra = values.pop('extra')
    instance_ref['extra'].update(extra)
    values['tags'] = []
    del values['name']
    instance_ref.update(values)
    session.add(instance_ref)
    session.commit()
    session.close()


def write_api_db(Session, inst_obj, cell_id):
    session = Session()
    mapping_model = api_models.InstanceMapping
    mapping_ref = mapping_model()
    mapping_ref.instance_uuid = inst_obj.uuid
    mapping_ref.cell_id = cell_id
    mapping_ref.project_id = instance.project_id
    session.add(mapping_ref)
    session.commit()
    session.close()


def write_neutron_db(Session, port):
    session = Session()
    port_ref = models_v2.Port()
    values = dict(port)
    port_ref.fixed_ips = [models_v2.IPAllocation()]
    fixed_ip_dict = dict(values.pop('fixed_ips')[0])
    fixed_ip_dict['ip_address'] = str(fixed_ip_dict['ip_address'])
    port_ref.fixed_ips[0].update(fixed_ip_dict)
    port_ref.update(values)
    port_ref.mac_address = str(port_ref.mac_address)
    session.add(port_ref)
    session.commit()


if __name__ == "__main__":
    parsed_args = parser.parse_args()
    nova_engine = create_engine(parsed_args.db_conn)
    NovaSession = sessionmaker(bind=nova_engine)
    api_engine = create_engine(api_database_connect)
    APISession = sessionmaker(bind=api_engine)
    neutron_engine = create_engine(neutron_database_connect)
    NeutronSession = sessionmaker(bind=neutron_engine)
    instance_objs, port_objs = get_instances_with_cached_ips(parsed_args.project_id, parsed_args.user_id)
    for instance in instance_objs:
        write_nova_db(NovaSession, instance)
        write_api_db(APISession, instance, parsed_args.cell_id)
    #for port in port_objs:
    #    write_neutron_db(NeutronSession, port)
