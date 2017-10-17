from django.utils.translation import ugettext_lazy as _

from control_panel.ansible_helpers import AnsibleInventory


HOSTS_CHOICES = AnsibleInventory().hosts_to_choices

RATE_CHOICES = (
    (1, _('Kbps')),
    (2, _('Mbps')),
    (3, _('Gbps')),
)

TIME_CHOICES = (
    (1, _('milliseconds')),
)

TRAFFIC_TYPE_CHOICES = (
    (None, _('----')),
    (1, _('Outgoing')),
    (2, _('Incoming'))
)

ACTION_CHOICES = (
    (1, _('Delete')),
)

