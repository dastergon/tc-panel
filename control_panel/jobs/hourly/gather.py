from control_panel.ansible_helpers import AnsibleInventory
from control_panel.deploy import AnsibleDeploy

from django_extensions.management.jobs import HourlyJob

class Job(HourlyJob):
    help = "Host Information Gathering Job."

    DEFAULT_OPTIONS = {
        'ansible_connection': 'ssh',
        'module_path': '/path/to/my/modules',
        'forks': 100,
        'ansible_remote_user': None,
        'ansible_ssh_private_key_file': None,
        'ansible_ssh_common_args': None,
        'ansible_ssh_extra_args': None,
        'ansible_become_user': None,
        'ansible_become_method': None,
        'ansible_become_user': None,
        'check': False
    }

    def execute(self):
        inventory = AnsibleInventory()
        all_hosts = inventory.unique_hosts_data
        global_options = inventory.global_options
        host_options = self.DEFAULT_OPTIONS.copy()
        host_options.update(global_options[0])
        for host in all_hosts:
            host_options.update(host["vars"])
            # handle status
            status = AnsibleDeploy(options=host_options).deploy(
                "hostname --ip-address", destination_host=host["name"], facts="yes")
