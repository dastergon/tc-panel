# TC Panel

### Authors

* Pavlos Ratis

### Prerequisites
Before proceeding you need to install the following dependencies:

- Python 2.7+
- Django 1.10+
- Ansible 2.3+

In addition you should have created an SSH key and your user should be created within the target Linux
system with the proper permissions. To allow your user execute commands with Ansible as root, which is
required for TC Panel your user should have passwordless sudo.

### Installation Process (Manual)
In order to install and test the application locally, you need to execute the following sequence of commands.

Go to the project folder:

    cd /path/to/tc-panel


Copy the local_settings.py.sample sample to a regular file:

    cp local_settings.py.sample local_settings.py


In the /path/to/tc-panel/tc-panel/settings.py the variable ANSIBLE_INVENTORY should be declared to the path that we want:

Example:

    ANSIBLE_INVENTORY = "/pat/to/hosts"

We can either use a pre-existing Ansible Inventory file or create one to specify all the parameters of the
project.

Example of the current Ansible Inventory file:

```
    [all:vars]
    ansible_user=foobaradmin
    ansible_become=true
    ansible_become_method=sudo
    ansible_become_user=root
    ansible_connection=ssh

    [namenodes]
    vm1.example.com ansible_host=1.1.1.1 ansible_port=10021
    vm2.example.com ansible_host=1.1.1.1 ansible_port=10022
```

Install all necessary Python prerequisites:

    pip install -r requirements.txt

Create database migrations:

    python manage.py makemigrations

The following command applies the migrations:

    python manage.py migrate

In order to load various testing fixtures(control_panel/fixtures) into the database, execute the following command:

    python manage.py loaddata <name_of_the_fixture>

To start the server, within the root directory of the project, execute:

    python manage.py runserver

Fetch host information:

    python manage.py runjobs hourly

Or add it to a cron job by adding the following entry:

    @hourly /path/to/my/project/manage.py runjobs hourly

