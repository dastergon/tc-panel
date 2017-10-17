from __future__ import unicode_literals

from django.contrib.auth.models import User, Group
from django.db import models
from django.template.defaultfilters import slugify

from control_panel.choices import *


class Audit(models.Model):
    timestamp = models.CharField(max_length=255)
    user = models.ForeignKey(User, null=True)
    status = models.CharField(max_length=255, default="")
    log = models.CharField(max_length=255)


class Region(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=40, unique=True)
    internal_max_bandwidth = models.FloatField(blank=True, default=0)
    internal_bw_rate = models.IntegerField(
        choices=RATE_CHOICES, null=True, blank=True)
    internal_latency = models.FloatField(blank=True, default=0)
    internal_latency_time_unit = models.IntegerField(
        choices=TIME_CHOICES, null=True, blank=True)
    external_max_bandwidth = models.FloatField(blank=True, default=0)
    external_bw_rate = models.IntegerField(
        choices=RATE_CHOICES, null=True, blank=True)
    packet_loss = models.FloatField(blank=True, default=0)
    packet_corruption_rate = models.FloatField(blank=True, default=0)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Region, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class InventoryGroup(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class InstanceType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    bandwidth = models.FloatField(blank=True, default=0)
    bw_rate = models.IntegerField(choices=RATE_CHOICES, null=True, blank=True)
    latency = models.FloatField(blank=True, default=0)
    latency_time_unit = models.IntegerField(
        choices=TIME_CHOICES, null=True, blank=True)
    packet_loss = models.FloatField(blank=True, default=0)
    packet_corruption_rate = models.FloatField(blank=True, default=0)

    def __str__(self):
        return self.name


class Host(models.Model):
    name = models.CharField(max_length=255, unique=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True)
    instance_type = models.ForeignKey(
        InstanceType, on_delete=models.CASCADE, null=True)
    interface = models.CharField(max_length=255, null=True)
    cpu = models.CharField(max_length=255, default='')
    memory = models.CharField(max_length=255, default='')
    distribution = models.CharField(max_length=255, default='')
    kernel = models.CharField(max_length=255, default='')
    ip_address = models.GenericIPAddressField()
    is_active = models.BooleanField(default=False)
    inventory_groups = models.ManyToManyField(InventoryGroup)

    def __str__(self):
        return self.name


class WAN(models.Model):
    name = models.CharField(max_length=255, unique=True)
    bandwidth = models.FloatField(blank=True, default=0)
    bw_rate = models.IntegerField(choices=RATE_CHOICES, null=True, blank=True)
    latency = models.FloatField(blank=True, default=0)
    latency_time_unit = models.IntegerField(
        choices=TIME_CHOICES, null=True, blank=True)
    packet_loss = models.FloatField(blank=True, default=0)
    packet_corruption_rate = models.FloatField(blank=True, default=0)

    def __str__(self):
        return self.name


class Rule(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True)
    interface = models.CharField(max_length=255)
    target_region = models.ForeignKey(
        Region, on_delete=models.CASCADE, null=True)
    target_host = models.ForeignKey(
        Host, on_delete=models.CASCADE, null=True, related_name="target_host")
    target_ip_address = models.GenericIPAddressField(null=True, blank=True)
    port_number = models.IntegerField(unique=True, null=True, blank=True)
    src_port_number = models.IntegerField(unique=True, null=True, blank=True)
    traffic_type = models.IntegerField(
        choices=TRAFFIC_TYPE_CHOICES, null=True, blank=True)
    bandwidth = models.FloatField(blank=True, default=0)
    bw_rate = models.IntegerField(choices=RATE_CHOICES, null=True, blank=True)
    latency = models.FloatField(blank=True, default=0)
    latency_time_unit = models.IntegerField(
        choices=TIME_CHOICES, null=True, blank=True)
    packet_loss = models.FloatField(blank=True, default=0)
    packet_corruption_rate = models.FloatField(blank=True, default=0)
    is_deployed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class RuleGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rule = models.ManyToManyField(Rule)
    description = models.CharField(max_length=255, default="")
    is_deployed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TrafficControlGroup(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    rule_group = models.ForeignKey(RuleGroup, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    cidr = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default="")
    is_deployed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    group = models.ManyToManyField(Group)

    def __str__(self):
        return self.user.username
