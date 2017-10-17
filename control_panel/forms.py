from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe

from control_panel.models import WAN, Host, InstanceType, Region, Rule, RuleGroup
from control_panel.choices import *


class UserForm(forms.ModelForm):
    name = forms.CharField(label='Full Name', widget=forms.TextInput(
        attrs={'class': 'form-control'}))
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.CharField(widget=forms.EmailInput(
        attrs={'class': 'form-control'}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('name', 'username', 'email', 'password', 'confirm_password')

    def clean_name(self):
        full_name = self.cleaned_data.get('name').split()
        if len(full_name) == 1:
            self.instance.first_name = full_name[0]
        elif len(full_name) >= 3:
            self.instance.first_name = full_name[0]
            self.instance.last_name = " ".join(full_name[1:])
        else:
            self.instance.first_name = full_name[0]
            self.instance.last_name = full_name[1]
        return self.cleaned_data

    def clean(self):
        super(UserForm, self).clean()
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        email = self.cleaned_data.get('email')
        if not password:
            raise forms.ValidationError(
                mark_safe("Empty password. Try again."))
        if password and password != confirm_password:
            raise forms.ValidationError(
                mark_safe("Passwords do not match. Try again."))
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email already exists.")
        return self.cleaned_data


class LoginForm(forms.ModelForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'password')

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise forms.ValidationError(
                "Authentication failed. Please try again.")
        return self.cleaned_data


class AddUserGroupForm(forms.ModelForm):
    group = forms.CharField(label='Group Name', widget=forms.TextInput(
        attrs={'class': 'form-control'}))

    class Meta:
        model = Group
        fields = ('group',)


class UserProfileForm(forms.Form):
    user = forms.ModelChoiceField(label="Select User", queryset=User.objects.all(
    ), widget=forms.Select(attrs={"class": "form-control"}))
    group = forms.ModelChoiceField(label="Select Group", queryset=Group.objects.all(
    ), widget=forms.Select(attrs={"class": "form-control"}))


class AddRuleGroupForm(forms.ModelForm):
    name = forms.CharField(label='Group Name')
    description = forms.CharField(label='Description', required=False)

    class Meta:
        model = RuleGroup
        fields = ('name', 'description')
        exclude = ('is_deployed', 'is_active',)


class HostForm(forms.ModelForm):
    name = forms.CharField(required=False)
    instance_type = forms.CharField(label="Instance Type", required=False)
    ip_address = forms.CharField(label="IP Address", required=False)
    region = forms.ModelChoiceField(
        label="Geographical Region", queryset=Region.objects.all(), required=False)

    class Meta:
        model = Host
        fields = ('name', 'ip_address', 'region')


class AddRegionForm(forms.ModelForm):
    name = forms.CharField(label='Geographical Region', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., EU North'}))
    slug = forms.CharField(label='Short name', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., eu-north-1'}), required=False)
    internal_max_bandwidth = forms.FloatField(
        label='Max Internal Bandwidth', required=False)
    internal_bw_rate = forms.ChoiceField(
        label='Internal Bandwidth Rate', choices=RATE_CHOICES, required=False)
    external_max_bandwidth = forms.FloatField(
        label='Max External Bandwidth', required=False)
    external_bw_rate = forms.ChoiceField(
        label='External Bandwidth Rate', choices=RATE_CHOICES, required=False)
    internal_latency = forms.IntegerField(initial=0, required=False)
    internal_latency_time_unit = forms.ChoiceField(
        choices=TIME_CHOICES, required=False)
    packet_loss = forms.IntegerField(label='Packet loss(%)', initial=0, widget=forms.NumberInput(
        attrs={"min": 0, "max": 100}), required=False)
    packet_corruption_rate = forms.IntegerField(
        label='Packet corruption rate (%)', initial=0, widget=forms.NumberInput(attrs={"min": 0, "max": 100}), required=False)

    class Meta:
        model = Region
        fields = ('name', 'slug', 'internal_max_bandwidth', 'internal_bw_rate',
                  'external_max_bandwidth', 'external_bw_rate',
                  'internal_latency', 'internal_latency_time_unit',
                  'packet_loss', 'packet_corruption_rate')


class AddWANForm(forms.ModelForm):
    name = forms.CharField(label='Name', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., eu-west_us-east'}))
    bandwidth = forms.FloatField(label='Max Bandwidth', required=False)
    bw_rate = forms.ChoiceField(
        label='Bandwidth rate', choices=RATE_CHOICES, required=False)
    latency = forms.IntegerField(required=False, initial=0)
    latency_time_unit = forms.ChoiceField(choices=TIME_CHOICES, required=False)
    packet_loss = forms.IntegerField(label='Packet loss(%)', initial=0, widget=forms.NumberInput(
        attrs={"min": 0, "max": 100}), required=False)
    packet_corruption_rate = forms.IntegerField(
        label='Packet corruption rate (%)', initial=0, widget=forms.NumberInput(attrs={"min": 0, "max": 100}), required=False)

    class Meta:
        model = WAN
        fields = ('name', 'bandwidth', 'bw_rate', 'latency',
                  'latency_time_unit', 'packet_loss',
                  'packet_corruption_rate')


class AddInstanceTypeForm(forms.ModelForm):
    name = forms.CharField(label='Instance Type', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., general-small'}))
    bandwidth = forms.FloatField(
        label='Max Bandwidth', initial=0, required=False)
    bw_rate = forms.ChoiceField(
        label='Bandwidth rate', choices=RATE_CHOICES, required=False)
    latency = forms.IntegerField(required=False, initial=0)
    latency_time_unit = forms.ChoiceField(choices=TIME_CHOICES, required=False)
    packet_loss = forms.IntegerField(label='Packet loss(%)', initial=0, widget=forms.NumberInput(
        attrs={"min": 0, "max": 100}), required=False)
    packet_corruption_rate = forms.IntegerField(
        label='Packet corruption rate (%)', initial=0, widget=forms.NumberInput(attrs={"min": 0, "max": 100}), required=False)

    class Meta:
        model = InstanceType
        fields = ('name', 'bandwidth', 'bw_rate',
                  'latency', 'latency_time_unit',
                  'packet_loss', 'packet_corruption_rate')


class ConfigureHostForm(forms.ModelForm):
    host = forms.ModelChoiceField(queryset=Host.objects.all())
    interface = forms.CharField(label='Network Interface', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., eth0'}))
    instance_type = forms.ModelChoiceField(queryset=InstanceType.objects.all(
    ), widget=forms.Select(attrs={"onChange": 'changeProfile()'}), required=False)
    ip_address = forms.CharField(label="IP Address", required=False)
    region = forms.ModelChoiceField(
        label="Geographical Region", queryset=Region.objects.all(), required=False)

    class Meta:
        model = Host
        fields = ('host', 'ip_address', 'interface', 'instance_type', 'region')


class AddRuleForm(forms.ModelForm):
    region = forms.ModelChoiceField(
        label="Source Region", queryset=Region.objects.all())
    host = forms.ModelChoiceField(
        queryset=Host.objects.exclude(region__isnull=True))
    interface = forms.CharField(label='Network Interface', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., eth0'}))
    instance_type = forms.ModelChoiceField(queryset=InstanceType.objects.all(
    ), widget=forms.Select(attrs={"onChange": 'changeProfile()'}), required=False)
    target_region = forms.ModelChoiceField(
        label="Target Region", queryset=Region.objects.all(), required=False)
    target_ip_address = forms.CharField(
        label='Target Destination CIDR Block / IP Address',  required=False)
    target_host = forms.ModelChoiceField(
        queryset=Host.objects.exclude(region__isnull=True))
    port_number = forms.IntegerField(label="Target Destination Port #", widget=forms.NumberInput(
        attrs={"min": 0, "max": 65536}), required=False)
    src_port_number = forms.IntegerField(label="Target Source Port #", widget=forms.NumberInput(
        attrs={"min": 0, "max": 65536}), required=False)
    traffic_type = forms.ChoiceField(choices=TRAFFIC_TYPE_CHOICES, widget=forms.Select(
        attrs={"onChange": 'trafficChange()'}), required=False)
    bandwidth = forms.FloatField(
        label='Max Bandwidth', initial=0, required=False)
    bw_rate = forms.ChoiceField(
        label='Bandwidth rate', choices=RATE_CHOICES, required=False)
    latency = forms.IntegerField(initial=0, required=False)
    latency_time_unit = forms.ChoiceField(choices=TIME_CHOICES, required=False)
    packet_loss = forms.IntegerField(label='Packet loss(%)', initial=0, widget=forms.NumberInput(
        attrs={"min": 0, "max": 100}), required=False)
    packet_corruption_rate = forms.IntegerField(
        label='Packet corruption rate (%)', initial=0, widget=forms.NumberInput(attrs={"min": 0, "max": 100}), required=False)

    class Meta:
        model = Rule
        fields = ('region',  'host', 'interface', 'src_port_number', 'instance_type', 'traffic_type', 'target_region', 'target_host',
                  'target_ip_address', 'port_number', 'bandwidth', 'bw_rate', 'latency', 'latency_time_unit', 'packet_loss', 'packet_corruption_rate')


class ApplyRegionForm(forms.Form):
    # remove required and fix action - region forms
    cidr = forms.CharField(
        label='Multiple Host Selection via CIDR Block', required=False)
    interface = forms.CharField(label='Network Interface', widget=forms.TextInput(
        attrs={'placeholder': 'i.e., eth0'}))
    instance_type = forms.ModelChoiceField(queryset=InstanceType.objects.all(
    ), widget=forms.Select(attrs={"onChange": 'changeProfile()'}), required=False)
    region = forms.ModelChoiceField(
        label="Geographical Region", queryset=Region.objects.all(), required=False)


class ActionsForm(forms.Form):
    actions = forms.ChoiceField(choices=ACTION_CHOICES)
