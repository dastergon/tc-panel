from django.conf.urls import url, include
from control_panel import views

import notifications.urls


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'panel/region/(?P<region_name>[\w-]+)/$', views.list_region_hosts, name='list_region_hosts'),
    url(r'panel/(?P<host_name>[\w.]+)/$', views.list_host_rules, name='list_host_rules'),
    url(r'panel/hosts/all/$', views.list_all_hosts, name='list_all_hosts'),
    url(r'^panel$', views.panel, name='panel'),
    url(r'^register/$', views.register, name='register'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^rule/list/all/$', views.list_all_rules, name='list_all_rules'),
    url(r'^rule/add/$', views.add_rule, name='add_rule'),
    url(r'^rule/delete/$', views.delete_rule, name='delete_rule'),
    url(r'^region/add/$', views.add_region, name='add_region'),
    url(r'^hosts/configure/$', views.configure_hosts, name='configure_hosts'),
    url(r'^region/delete/$', views.delete_region, name='delete_region'),
    url(r'^rule_group/list/all/$', views.list_deployment_groups, name='list_deployment_groups'),
    url(r'^rule_group/add/$', views.add_rule_group, name='add_rule_group'),
    url(r'^rule_group/(?P<rule_group_name>[\w+-]+)/rules/$', views.list_all_rules, name='list_rule_group_rules'),
    url(r'^rule_group/delete/$', views.delete_rule_group, name='delete_rule_group'),
    url(r'^instance_type/add/$', views.add_instance_type, name='add_instance_type'),
    url(r'^instance_type/delete/$', views.delete_instance_type, name='delete_instance_type'),
    url(r'^wan/add/$', views.add_wan, name='add_wan'),
    url(r'^wan/delete/$', views.delete_wan, name='delete_wan'),
    url(r'^notifications/', include(notifications.urls, namespace='notifications')),
    url(r'^messages/$', views.view_notifications, name='view_notifications'),
    url(r'^dismiss_message/$', views.dismiss_message, name='dismiss_message'),
    url(r'^history/$', views.history, name='history'),
    url(r'^groups/$', views.groups, name='groups'),
    url(r'^overview/$', views.overview, name='overview'),
]
