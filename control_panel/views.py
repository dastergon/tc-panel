from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout

from control_panel.forms import AddUserGroupForm, ConfigureHostForm, AddWANForm, AddInstanceTypeForm, HostForm, ApplyRegionForm, UserForm, LoginForm, UserProfileForm, AddRegionForm, AddRuleForm, ActionsForm, AddRuleGroupForm
from control_panel.models import InstanceType, WAN, Host, Audit, Region, Rule, RuleGroup
from control_panel.deploy import AnsibleDeploy
from control_panel.ansible_helpers import AnsibleInventory
from control_panel.choices import RATE_CHOICES, TIME_CHOICES

import datetime
import json
import ipaddr
import operator

from notifications.signals import notify
from notifications.models import Notification


def _update_topology_map(hosts):
    topology_map = ["""<?xml version=\'1.0\' encoding=\'UTF-8\'?>
<!--Autogenerated by tc-panel-->
<topology>""" ]
    for host in hosts:
        if host.region:
            topology_map.append("""
    <node name=\'{0}\' rack=\'/{1}/default-rack\'/>
    <node name=\'{2}\' rack=\'/{1}/default-rack\'/>""".format(host, host.region.slug, host.ip_address))
    topology_map.append("\n</topology>")
    cmd = """cat > /etc/hadoop/conf/topology.map << EOF
            {0}
EOF""".format(" ".join(topology_map))
    return cmd

def _init_ansible(cmd, facts):
    inventory = AnsibleInventory()
    all_hosts = inventory.unique_hosts_data
    global_options = inventory.global_options
    host_options = inventory.DEFAULT_OPTIONS.copy()
    host_options.update(global_options[0])
    for host in all_hosts:
        host_options.update(host["vars"])
        status = AnsibleDeploy(options=host_options).deploy(
            cmd, destination_host=host["name"], facts=facts)
        # TODO: check the status


def generate_tc_command(rule, override=False, deactivate=False):
    """Command generation logic from UI to tcconfig commands"""
    exclude_network = []
    tcset_commands = []
    final_command = []
    if deactivate:
        final_command.append("tcdel --device " + rule.interface + " --all")
    else:
        target_hosts = [rule.target_host]
        if rule.target_host.region and (not rule.target_host):
            target_hosts = Host.objects.filter(
                region=rule.target_host.region).exclude(name=rule.host.name)
        latency = 0
        for target_host in target_hosts:
            tcset = {}
            # internal
            bandwidths = [(rule.bandwidth, rule.bw_rate),
                          (target_host.region.internal_max_bandwidth,
                           target_host.region.internal_bw_rate),
                          (target_host.instance_type.bandwidth,
                           target_host.instance_type.bw_rate)]

            latency = rule.latency + rule.host.instance_type.latency + \
                rule.host.region.internal_latency
            packet_loss = rule.packet_loss + \
                rule.host.instance_type.packet_loss + rule.host.region.packet_loss
            packet_corruption_rate = rule.packet_corruption_rate + \
                rule.host.instance_type.packet_corruption_rate + \
                rule.host.region.packet_corruption_rate
            bandwidths = [tp for tp in bandwidths if all(tp)]

            if rule.host.region != target_host.region:
                # external
                wan = WAN.objects.get(name="{0}_{1}".format(
                    target_host.region.slug, rule.host.region.slug))
                if not wan:
                    wan = WAN.objects.get(name="{0}_{1}".format(
                        rule.host.region.slug, target_host.region.slug))
                    if not wan:
                        wan = WAN.objects.get(
                            name="{0}".format(rule.host.region.slug))
                bandwidths = [(rule.bandwidth, rule.bw_rate),
                              (rule.host.region.external_max_bandwidth,
                               rule.host.region.external_bw_rate),
                              (target_host.region.external_max_bandwidth,
                               target_host.region.external_bw_rate),
                              (target_host.instance_type.bandwidth,
                               target_host.instance_type.bw_rate),
                              (wan.bandwidth, wan.bw_rate)]

                bandwidths = [tp for tp in bandwidths if all(tp)]
                latency += target_host.region.internal_latency + wan.latency
                packet_loss += target_host.region.packet_loss + wan.packet_loss
                packet_corruption_rate += target_host.region.packet_corruption_rate + \
                    wan.packet_corruption_rate

            min_bandwidth, min_bandwidth_rate = min(
                bandwidths, key=operator.itemgetter(1, 0))
            rate_choices = dict(RATE_CHOICES)
            time_choices = dict(TIME_CHOICES)
            tcset['rate'] = str(int(min_bandwidth)) + \
                    str(rate_choices[min_bandwidth_rate])
            tcset['delay'] = str(int(latency)) + \
                    str(time_choices[rule.latency_time_unit])
            tcset['device'] = rule.interface
            tcset['loss'] = int(rule.packet_loss or 0)
            tcset['corrupt'] = rule.packet_corruption_rate
            tcset['port'] = rule.port_number
            tcset['src-port'] = rule.src_port_number
            tcset['dst-network'] = rule.target_ip_address or target_host.ip_address
            tcset['direction'] = rule.traffic_type

            if not rule.traffic_type:
                tcset['direction'] = 'outgoing'
                tcset_commands.append(tcset)
                shallow_copy_tcset = tcset.copy()
                shallow_copy_tcset['direction'] = 'incoming'
                tcset_commands.append(shallow_copy_tcset)

        for cmd in tcset_commands:
            construct_cmd = []
            for key, value in cmd.items():
                if value:
                    construct_cmd.append("--" + key + " " + str(value))
            final_command.append(
                "tcset " + " ".join(construct_cmd) + " --change;")

    return " ".join(final_command)


def index(request):
    """The landing page for the anonymous users"""
    if request.user.is_authenticated():
        return HttpResponseRedirect("/panel")
    return render(request, "index.html")


@login_required
def overview(request):
    """Overview of the emulation"""
    rule_group = RuleGroup.objects.all()
    nodes = []
    edges = []
    regions = set()
    for tc in rule_group:
        for rule in tc.rule.all():
            regions.add(rule.host.region)
        counter = 0
        hosts = set()
        for region in regions:
            tc_counter = counter
            hosts = set()
            nodes.append({'id': tc_counter, 'label': str(region)})
            for rule in tc.rule.all():
                if rule.host.region == region and rule.host not in hosts:
                    hosts.add(rule.host)
                    counter += 1
                    rule_counter = counter
                    nodes.append({'id': rule_counter, 'label': str(
                        rule.host.ip_address), 'group': str(region)})
                    edges.append(
                        {'from': tc_counter, 'to': rule_counter, 'length': str(200), 'label': 'TODO'})
            counter += 1
    return render(request, "birdseye.html", {"edges": edges, "nodes": nodes})


@login_required
def view_notifications(request):
    """View notifications"""
    user = User.objects.get(username=request.user.username)
    messages = user.notifications.unread()
    return render(request, "notifications.html", {"messages": messages})


@login_required
def groups(request):
    """The messages view that shows all the received messages from other peers """
    users = User.objects.all()
    if request.method == 'POST':
        add_user_group_form = AddUserGroupForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if "add_group" in request.POST:
            if add_user_group_form.is_valid():
                group_name = add_user_group_form.cleaned_data["group"]
                new_group, created = Group.objects.get_or_create(
                    name=group_name)
                # TODO: manage errors
                return HttpResponseRedirect('/groups')
            else:
                print(add_user_group_form.errors)
        elif "add_user_to_group" in request.POST:
            if profile_form.is_valid():
                user = User.objects.get(
                    username=profile_form.cleaned_data["user"])
                user.groups.add(profile_form.cleaned_data["group"])
                user.save()
                return HttpResponseRedirect('/groups')
            else:
                print(profile_form.errors)
    else:
        profile_form = UserProfileForm()
        add_user_group_form = AddUserGroupForm()
    return render(request, "groups.html", {'users': users,
                                           'profile_form': profile_form, 'add_user_group_form': add_user_group_form})


@login_required
def messages(request):
    """The messages view that shows all the received messages from other peers """
    user = User.objects.get(username=request.user.username)
    messages = user.notifications.unread()  # get the unread messages
    return render(request, "connect/messages.html", {'messages': messages})


@login_required
def dismiss_message(request):
    """Dismiss alert view that marks the alerts as read """
    message_id = request.POST.get('id')
    if request.is_ajax():
        alert = Notification.objects.get(id=int(message_id))
        alert.mark_as_read()
        alert.save()
    return HttpResponseRedirect('/')


@login_required
def deploy(request, selected_rule_groups):
    """Trigger Ansible and deploy commands via Ansible"""
    is_deploy = True if 'deploy' in request.POST else False
    is_undeploy = True if 'undeploy' in request.POST else False
    for rule_group_id in selected_rule_groups:
        rule_group = RuleGroup.objects.get(id=rule_group_id)
        message = []
        for rule in rule_group.rule.all():
            if rule.is_deployed:
                continue
            command = ""
            if is_deploy: command = generate_tc_command(rule)
            elif is_undeploy: command = generate_tc_command(rule, deactivate=True)

            if not command:  # if there are no args or rules to play with
                continue

            inventory = AnsibleInventory()
            hosts = inventory.unique_hosts_data
            global_options = inventory.global_options
            host_options = inventory.DEFAULT_OPTIONS.copy()
            host_options.update(global_options[0])
            host_vars = [host["vars"]
                            for host in hosts if host["name"] == rule.host.name]
            host_options.update(host_vars[0])
            status = AnsibleDeploy(options=host_options).deploy(
                command, rule.host.name, facts='no')

            if status == 0:
                rule_group.is_deployed = True
                if is_deploy:
                    rule.is_deployed = True
                    rule_group.is_active = True
                elif is_undeploy:
                    rule_group.is_active = False
                message.append("deployed")
            else:
                rule_group.is_deployed = False
                message.append("failed")
            rule_group.save()
        verb = "failed" if "failed" in message else "deployed"
        recipient = User.objects.get(username=request.user.username)
        notify.send(request.user, recipient=recipient, verb=verb)


@login_required
def panel(request):
    """Main Dashboard & Deployment operations"""
    if request.method == 'POST':
        add_rule_group = AddRuleGroupForm(request.POST)
        selected_rule_groups = request.POST.getlist('rule_group')
        if selected_rule_groups:
            deploy(request, selected_rule_groups)
    else:
        add_rule_group = AddRuleGroupForm()
    regions = Region.objects.all()
    rule_group = RuleGroup.objects.all()
    add_region = AddRegionForm()
    actions_form = ActionsForm()
    return render(request, "panel.html", {"add_region": add_region, "regions": regions,  "rule_group": rule_group, "add_rule_group": add_rule_group, "actions_form": actions_form})


@login_required
def configure_hosts(request):
    """Configure Host properties view"""
    hosts = Host.objects.all()
    hosts_form = ConfigureHostForm()
    actions_form = ApplyRegionForm()
    if request.method == 'POST':
        actions_form = ApplyRegionForm(request.POST)
        if actions_form.is_valid():
            selected_configurations = actions_form.cleaned_data
            selected_cidr = actions_form.cleaned_data["cidr"]
            if selected_cidr:
                cidr = ipaddr.IPNetwork(selected_cidr)
                for host in hosts:
                    if cidr.overlaps(ipaddr.IPNetwork(host.ip_address)):
                        host.region = selected_configurations["region"]
                        host.instance_type = selected_configurations[
                            "interface_type"]
                        host.interface = selected_configurations["interface"]
                        host.save()
            else:
                selected_hosts = request.POST.getlist('hosts')
                for host_id in selected_hosts:
                    host = Host.objects.filter(id=host_id).update(region=selected_configurations["region"],
                                                               instance_type=selected_configurations["instance_type"], interface=selected_configurations["interface"])

        hosts = Host.objects.all()
        cmd = _update_topology_map(hosts)
        _init_ansible(cmd, facts="no")

    else:
        print(actions_form.errors)

    return render(request, "configure_hosts.html", {"hosts": hosts, "hosts_form": hosts_form, "actions_form": actions_form})


@login_required
def history(request):
    """Show Audit logs"""
    history = Audit.objects.all()
    return render(request, "history.html", {"history": history})


@login_required
def list_deployment_groups(request):
    """List Deployment Groups"""
    rule_group = RuleGroup.objects.all()
    add_rule_group = AddRuleGroupForm()
    actions_form = ActionsForm()
    return render(request, "list_deployment_groups.html", {"add_rule_group": add_rule_group, "actions_form": actions_form, "rule_group": rule_group})


@login_required
def list_all_hosts(request):
    """List All Available Hosts"""
    hosts = Host.objects.all()
    hosts_form = HostForm()
    return render(request, "list_all_hosts.html", {"hosts_form": hosts_form, "hosts": hosts})


@login_required
def list_region_hosts(request, region_name=None):
    """List the Hosts of the Regions"""
    hosts = Host.objects.filter(region__slug=region_name)
    hosts_form = HostForm()
    return render(request, "list_region_hosts.html", {"region_name": region_name, "hosts_form": hosts_form, "hosts": hosts})


@login_required
def list_all_rules(request, rule_group_name=None):
    """List all Rules"""
    rules = Rule.objects.all()
    hosts = Host.objects.all()
    hosts_form = HostForm()
    if rule_group_name:
        rules = RuleGroup.objects.filter(name=rule_group_name)[0].rule.all()
    add_rule = AddRuleForm()
    actions_form = ActionsForm()
    return render(request, "list_all_rules.html", {"actions_form": actions_form, "add_rule": add_rule, "rules": rules, "hosts_form": hosts_form, "hosts": hosts})


@login_required
def list_host_rules(request, region_name=None, host_name=None):
    """List the Designated Rules of the Host"""
    hosts = Host.objects.filter(name=host_name)
    rules = Rule.objects.filter(host__name=host_name)
    hosts_form = HostForm()
    add_rule = AddRuleForm()
    actions_form = ActionsForm()
    return render(request, "list_host_rules.html", {"host_name": host_name, "actions_form": actions_form, "add_rule": add_rule, "rules": rules, "region_name": region_name, "hosts_form": hosts_form, "hosts": hosts})


@login_required
def add_wan(request):
    """Add Wide Area Network View"""
    if request.method == 'POST':
        add_wan = AddWANForm(request.POST)
        if add_wan.is_valid():
            wan = add_wan.save(commit=False)
            wan.save()
            _log_action(wan, attrs={'type': 'wan', 'action': 'create'})
            return HttpResponseRedirect('/wan/add')
        else:
            print(add_wan.errors)
    else:
        add_wan = AddWANForm()
    wans = WAN.objects.all()
    actions_form = ActionsForm()
    return render(request, "add_wan.html", {"add_wan": add_wan, "wans": wans, "actions_form": actions_form})


@login_required
def add_instance_type(request):
    """Add Instance Type View"""
    if request.method == 'POST':
        add_instance_type = AddInstanceTypeForm(request.POST)
        if add_instance_type.is_valid():
            instance_type = add_instance_type.save(commit=False)
            instance_type.save()
            _log_action(instance_type, attrs={
                        'type': 'instance_type', 'action': 'create'})
            return HttpResponseRedirect('/instance_type/add')
        else:
            print(add_instance_type.errors)
    else:
        add_instance_type = AddInstanceTypeForm()
    instance_types = InstanceType.objects.all()
    actions_form = ActionsForm()
    return render(request, "add_instance_type.html", {"add_instance_type": add_instance_type, "instance_types": instance_types, "actions_form": actions_form})


@login_required
def add_region(request):
    """Add Region View"""
    if request.method == 'POST':
        add_region = AddRegionForm(request.POST)
        if add_region.is_valid():
            region = add_region.save(commit=False)
            region.save()
            _log_action(region, attrs={'type': 'region', 'action': 'create'})
            return HttpResponseRedirect('/region/add')
        else:
            print(add_region.errors)
    else:
        add_region = AddRegionForm()
    regions = Region.objects.all()
    hosts = Host.objects.all()
    hosts_form = HostForm()
    actions_form = ActionsForm()
    return render(request, "add_region.html", {"hosts_form": hosts_form, "hosts": hosts, "add_region": add_region, "regions": regions, "actions_form": actions_form})


@login_required
def add_rule(request):
    """Add Rule View"""
    if request.is_ajax():
        region_id = request.GET.get('region')
        if not region_id:
            hosts = Host.objects.all().values('name')
        else:
            hosts = Host.objects.filter(region__id=region_id).values('name')
        return HttpResponse(json.dumps(list(hosts)), content_type="application/json")
    if request.method == 'POST':
        add_rule = AddRuleForm(request.POST)
        if add_rule.is_valid():
            data = add_rule.cleaned_data
            rule = add_rule.save(commit=False)
            rule.host = data["host"]
            rule.traffic_type = int(data["traffic_type"] or 0)
            if data["instance_type"]:
                rule.host.instance_type = data["instance_type"]
            rule.host.save()
            if rule.host.instance_type:
                rule.bandwidth = rule.host.instance_type.bandwidth
                rule.bw_rate = rule.host.instance_type.bw_rate
                rule.packet_loss = rule.host.instance_type.packet_loss
                rule.packet_corruption_rate = rule.host.instance_type.packet_corruption_rate
                rule.latency = rule.host.instance_type.latency
                rule.latency_time_unit = rule.host.instance_type.latency_time_unit
            rule.save()
            _log_action(rule.id, attrs={'type': 'rule', 'action': 'create'})
            return HttpResponseRedirect('/rule_group/add')
        else:
            print(add_rule.errors)
    else:
        add_rule = AddRuleForm()
    actions_form = ActionsForm()
    rules = Rule.objects.all()
    return render(request, "add_rule.html",
                  {"add_rule": add_rule, "rules": rules, "actions_form": actions_form})


@login_required
def add_rule_group(request):
    """Add Deployment Group View"""
    if request.method == 'POST':
        add_rule_group = AddRuleGroupForm(request.POST)
        add_rule = AddRuleForm(request.POST)
        if add_rule_group.is_valid():
            rule_group = add_rule_group.save()
            selected_hosts = request.POST.getlist('hosts')
            if selected_hosts:
                for src_host in selected_hosts:
                    for dst_host in selected_hosts:
                        if src_host != dst_host:
                            rule = Rule()
                            rule.host = Host.objects.get(id=src_host)
                            rule.target_host = Host.objects.get(id=dst_host)
                            rule.target_region = rule.target_host.region
                            if rule.host.instance_type:
                                rule.bandwidth = rule.host.instance_type.bandwidth
                                rule.latency = rule.host.instance_type.latency
                                rule.interface = rule.host.interface
                                rule.bw_rate = rule.host.instance_type.bw_rate
                                rule.packet_loss = rule.host.instance_type.packet_loss
                                rule.packet_corruption_rate = rule.host.instance_type.packet_corruption_rate
                                rule.latency_time_unit = rule.host.instance_type.latency_time_unit
                            rule.save()
                            rule_group.rule.add(rule)
            selected_rules = request.POST.getlist('rules')
            if selected_rules:
                for rule_id in selected_rules:
                    rule = Rule.objects.get(id=rule_id)
                    rule_group.rule.add(rule)
            rule_group.save()
            _log_action(rule_group.name, attrs={
                        'type': 'rule group', 'action': 'create'})
            return HttpResponseRedirect('/')
        else:
            print(add_rule_group.errors)
    else:
        add_rule_group = AddRuleGroupForm()
        add_rule = AddRuleForm()
    rules = Rule.objects.all()
    hosts = Host.objects.exclude(region__isnull=True)
    hosts_form = ConfigureHostForm()
    actions_form = ActionsForm()
    return render(request, "add_rule_group.html", {
        "add_rule": add_rule, "add_rule_group": add_rule_group,
        "rules": rules, "hosts": hosts,
        "hosts_form": hosts_form,
        "actions_form": actions_form})


@login_required
def delete_rule_group(request):
    """Delete Deployment Group View"""
    if request.method == 'POST':
        actions = ActionsForm(request.POST)
        if actions.is_valid():
            rule_groups = request.POST.getlist('rule_group')
            for rule_group_id in rule_groups:
                rule_group = RuleGroup.objects.get(id=rule_group_id)
                rule_group.rule.all().delete()
                rule_group.delete()
                _log_action(rule_group_id, attrs={
                            'type': 'rule group', 'action': 'delete'})
        else:
            print(actions.errors)
    return HttpResponseRedirect('/rule_group/add')


@login_required
def delete_region(request):
    """Delete region view"""
    if request.method == 'POST':
        actions = ActionsForm(request.POST)
        if actions.is_valid():
            regions = request.POST.getlist('region')
            for region_id in regions:
                Region.objects.get(id=region_id).delete()
                _log_action(region_id, attrs={
                            'type': 'region', 'action': 'delete'})
        else:
            print(actions.errors)
    return HttpResponseRedirect('/region/add')


@login_required
def delete_instance_type(request):
    """Delete instance type view"""
    if request.method == 'POST':
        actions = ActionsForm(request.POST)
        if actions.is_valid():
            instance_types = request.POST.getlist('instance_type')
            for instance_type_id in instance_types:
                InstanceType.objects.get(id=instance_type_id).delete()
                _log_action(instance_type_id, attrs={
                            'type': 'instance_type', 'action': 'delete'})
        else:
            print(actions.errors)
    return HttpResponseRedirect('/instance_type/add')


@login_required
def delete_wan(request):
    """Delete WAN rules"""
    if request.method == 'POST':
        actions = ActionsForm(request.POST)
        if actions.is_valid():
            wans = request.POST.getlist('wans')
            for wan_id in wans:
                WAN.objects.get(id=wan_id).delete()
                _log_action(wan_id, attrs={'type': 'wan', 'action': 'delete'})
        else:
            print(actions.errors)
    return HttpResponseRedirect('/wan/add')


@login_required
def delete_rule(request):
    """Delete rules view"""
    if request.method == 'POST':
        actions = ActionsForm(request.POST)
        if actions.is_valid():
            rules = request.POST.getlist('rules')
            for rule_id in rules:
                rule = Rule.objects.get(id=rule_id)
                inventory = AnsibleInventory()
                hosts = inventory.unique_hosts_data
                global_options = inventory.global_options
                host_options = inventory.DEFAULT_OPTIONS.copy()
                host_options.update(global_options[0])
                host_vars = [host["vars"]
                             for host in hosts if host["name"] == rule.host.name]
                host_options.update(host_vars[0])

                command = generate_tc_command(rule, deactivate=True)
                _log_action(rule_id, attrs={
                            'type': 'rule', 'action': 'delete'})
                status = AnsibleDeploy(options=host_options).deploy(
                    command, rule.host.name, facts='no')
                rule.delete()
                all_host_rules = Rule.objects.filter(host__name=rule.host.name)
                for host_rule in all_host_rules:
                    deploy_the_rest_of_the_rules = generate_tc_command(
                        host_rule, deactivate=True)
                    # TODO:  log
                    status = AnsibleDeploy(options=host_options).deploy(
                        deploy_the_rest_of_the_rules, host_rule.host.name, facts='no')
        else:
            print(actions.errors)
    return HttpResponseRedirect('/rule/add')


def register(request):
    """The registration view that enables the users to register """
    registered = False
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            registered = True
        else:
            print(user_form.errors)
    else:
        user_form = UserForm()
    return render(request, 'register.html', {'user_form': user_form,
                                             'registered': registered})


def login(request):
    """The login view that enables users to login to the platform """
    authenticated = False
    login_form = LoginForm(request.POST)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                auth_login(request, user)
                authenticated = True
                return redirect('index')
            else:
                print(login_form.errors)
        else:
            print("Invalid login, Try again.")
    else:
        login_form = LoginForm()

    return render(request, 'login.html',
                  {'login_form': login_form, 'authenticated': authenticated})


@login_required
def logout(request):
    """The user logout view"""
    auth_logout(request)
    return HttpResponseRedirect('/')


def _log_action(entity, attrs):
    """Audit events view"""
    timestamp = str(datetime.datetime.now())
    if attrs['action'] == 'delete':
        log = "Deleted {0}".format(attrs['type'].capitalize())
    elif attrs['action'] == 'create':
        log = "Created {0}".format(entity)
    log_command = Audit(timestamp=timestamp, log=log)
    log_command.save()