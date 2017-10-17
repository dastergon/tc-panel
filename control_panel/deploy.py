from collections import namedtuple
from django.conf import settings
from django.contrib.auth.models import User

from control_panel.models import InventoryGroup, Host, Audit

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager

from notifications.signals import notify

import datetime


class ResultCallback(CallbackBase):
    """A callback plugin used for managing the results as they come in"""

    def v2_runner_on_ok(self, result, **kwargs):
        """This method stores the result in an instance attribute for retrieval later"""
        host = result._host
        results = result._result
        if 'ansible_facts' in results:
            host_entry, created = Host.objects.update_or_create(name=results['ansible_facts']['ansible_fqdn'],
                                                                defaults={
                'ip_address': results['ansible_facts']['ansible_default_ipv4']['address'],
                'cpu': results['ansible_facts']['ansible_processor_cores'],
                'memory': str(results['ansible_facts']['ansible_memory_mb']['real']['total']) + 'MB',
                'distribution': results['ansible_facts']['ansible_lsb']['description'],
                'kernel': results['ansible_facts']['ansible_kernel'],
                'region': None,
                'is_active': True})

            for group in host.groups:
                group_entry, created = InventoryGroup.objects.update_or_create(
                    name=group.name)
                host_entry.inventory_groups.add(group_entry)

        # Checks if the command returned error
        if results['stderr_lines']:
            # Send notifications to all the superusers
            superusers = User.objects.filter(is_superuser=True)
            for superuser in superusers:
                recipient = User.objects.get(username=superuser)
            message = "rules_failed"
            notify.send(recipient, recipient=recipient,
                        description="Host {0} - Output: {1}".format(
                            host, results['stderr_lines']),
                        verb=message)


class AnsibleDeploy(object):
    """A class used to trigger and deploy commands to the hosts via Ansible"""

    def __init__(self, options, stdout_callback='default', vault_pass='secret'):
        Options = namedtuple('Options', ['verbosity', 'connection', 'module_path', 'forks', 'host', 'remote_port', 'remote_user',
                                         'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'become', 'become_method', 'become_user', 'check'])
        self.options = Options(connection=options["ansible_connection"],
                               module_path=options["module_path"],
                               forks=options["forks"],
                               remote_user=options["ansible_user"],
                               remote_port=options["ansible_port"],
                               host=options["ansible_host"],
                               private_key_file=options[
                                   "ansible_ssh_private_key_file"],
                               ssh_common_args=options[
                                   "ansible_ssh_common_args"],
                               ssh_extra_args=options[
                                   "ansible_ssh_extra_args"],
                               become=options["ansible_become"],
                               become_method=options["ansible_become_method"],
                               become_user=options["ansible_become_user"],
                               verbosity=1,
                               check=options["check"])
        self.stdout_callback = stdout_callback
        self.vault_pass = vault_pass
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.passwords = dict(vault_pass=self.vault_pass)

    def _log_deployment(self, cmd, host):
        """Log the deployment events"""
        timestamp = str(datetime.datetime.now())
        log_command = Audit(timestamp=timestamp,
                            log="Deploying %s to %s" % (cmd, host))
        return log_command.save()

    def deploy(self, cmd, destination_host, facts='no'):
        """Deploy commands via Ansible"""
        self.inventory = Inventory(
            loader=self.loader, variable_manager=self.variable_manager, host_list=settings.ANSIBLE_INVENTORY)
        self.variable_manager.set_inventory(self.inventory)
        results_callback = ResultCallback()
        tasks = [dict(action=dict(module='shell', args=dict(_raw_params=cmd)), register='shell_out'),
                 dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}')))]
        print(cmd)
        if not cmd:
            tasks = None

        play_source = dict(
            name="Deploy Rules @ {0}".format(destination_host),
            gather_facts=facts,
            hosts=[destination_host],
            tasks=tasks,)
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        self._log_deployment(cmd, destination_host)

        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
                #stdout_callback="debug",
                stdout_callback=results_callback,
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
        return result
