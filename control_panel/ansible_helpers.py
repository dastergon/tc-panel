from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager


class AnsibleInventory(object):
    """A helper class that interacts with the Ansible Inventory"""

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

    def __init__(self):
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.inventory = Inventory(
            loader=self.loader, variable_manager=self.variable_manager, host_list=settings.ANSIBLE_INVENTORY)
        self.hosts_data = self._serialize(self.inventory)
        self.unique_hosts_data = {host[
            "name"]: host for host in self.hosts_data if not host["name"] == "all"}.values()

    @property
    def global_options(self):
        """Returns the global Inventory options(configs) from hosts"""
        return [host["vars"] for host in self.hosts_data if host["name"] == "all"]

    @property
    def hosts_list(self):
        """Returns a list with the available hosts"""
        hosts = []
        for host in self.unique_hosts_data:
            if not host["name"] == "all":
                hosts.append(host["address"] + host["vars"]["ansible_port"])
        return hosts

    @property
    def hosts_to_choices(self):
        """Convert host names to choices """
        host_choices = ()
        host_choices += (' ', _("------")),
        for host in self.unique_hosts_data:
            host_choices += ((host["name"], _(host["name"],),),)
        return host_choices

    def _serialize(self, inventory):
        """Serialize data from Inventory file"""
        if not isinstance(inventory, Inventory):
            return dict()
        data = []
        for group in inventory.get_groups():
            if group != 'all':
                for host in inventory.get_group(group).hosts:
                    data.append(host.serialize())
            elif group == 'all':
                data.append(inventory.get_group('all').serialize())
        return data
