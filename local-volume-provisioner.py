


import json
import subprocess
import os
import time

vol_base_dir = os.getenv('VOLUMES_BASE_DIR', '/tmp/local_volumes')
host_ip = os.getenv('HOST_IP')
if not host_ip:
	fetch_nics_script = os.getenv('FETCH_PHYSICAL_NICS_SCRIPT', '/opt/pf9/hostagent/extensions/fetch_physical_nics')
	out = subprocess.check_output(['sudo', fetch_nics_script])
	parsed = json.loads(out)
	default_nic = parsed['default']
	host_ip = parsed[default_nic]
namespace = os.getenv('NAMESPACE', 'default')
print('host ip: %s' % host_ip)


def pv_json_string(name, local_path, storage_request, host_name):
    return {
        'apiVersion': 'v1',
        'kind': 'PersistentVolume',
        'metadata': {
            'name': name,
        },
        'spec': {
            'capacity': {
                'storage': storage_request,
            },
            'volumeMode': 'Filesystem',
            'accessModes': [
                'ReadWriteOnce',
            ],
            'storageClassName': 'local-storage',
            'local': {
                'path': local_path,
            },
            'nodeAffinity': {
                'required': {
                    'nodeSelectorTerms': [
                        {
                            'matchExpressions': [
                                {
                                    'key': 'kubernetes.io/hostname',
                                    'operator': 'In',
                                    'values': [
                                        host_name,
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }


def create_new_volumes():
    out = subprocess.check_output(['kubectl', 'get', '-n', namespace, '-ojson', 'pvc'])
    parsed = json.loads(out)
    for pvc in parsed['items']:
        name = pvc['metadata']['name']
        if pvc['status']['phase'] != 'Pending':
            continue
        print('pending pvc: %s' % name)
        storage_request = pvc['spec']['resources']['requests']['storage']
        print('storage request: %s' % storage_request)
        sanitized_host_ip = host_ip.replace('.', '-')
        pv_name = '%s-%s' % (name, sanitized_host_ip)
        print('pv_name: %s' % pv_name)
        pv_dir = os.path.join(vol_base_dir, pv_name)
        print('pv_dir: %s' % pv_dir)
        if os.path.exists(pv_dir):
            print('%s already exists' % pv_dir)
            continue
        obj = pv_json_string(pv_name, pv_dir, storage_request, host_ip)
        json_str = json.dumps(obj, indent=2)
        # print('pv json string: %s' % json_str)
        os.mkdir(pv_dir, 0o777)
        print('created directory %s' % pv_dir)
        child = subprocess.Popen(['kubectl', 'apply', '-f', '-'],
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = child.communicate(bytes(json_str))
        if child.returncode != 0:
            print('kubectl failed with stderr: %s' % stderr)
        else:
            print('created pv %s' % pv_name)
            print('')


def delete_released_volumes():
    out = subprocess.check_output(['kubectl', 'get', '-ojson', 'pv'])
    parsed = json.loads(out)
    for pv in parsed['items']:
        pv_name = pv['metadata']['name']
        if pv['status']['phase'] != 'Released':
            continue
        print('found released pv: %s' % pv_name)
        pv_dir = os.path.join(vol_base_dir, pv_name)
        if not os.path.exists(pv_dir):
            print('%s does not belong to this node' % pv_name)
            continue
        subprocess.check_output(['kubectl', 'delete', 'pv', pv_name])
        subprocess.check_output(['sudo', 'rm', '-rf', pv_dir])
        print('deleted %s' % pv_dir)
        print('')


while True:
    time.sleep(2.0)
    delete_released_volumes()
    create_new_volumes()


