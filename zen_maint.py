import zenAPI.zenApiLib
import argparse
import datetime
import re
import time
import yaml


APP_FILE = 'applications.yaml'


def check_org_exists(routers, uid, org_name, org_type):
    d_router = routers['Device']
    response = d_router.callMethod('objectExists', uid=uid)
    if not response['result']['success']:
        print("Could not check presence of {} {} in Zenoss.".format(org_type, org_name))
        exit(1)
    if not response['result']['exists']:
        print("The {} {} does not exist in Zenoss.".format(org_type, org_name))
        exit(1)
    return


def start_format(start):
    if start == 'now':
        start_time = datetime.datetime.now()
    else:
        if re.match(r'\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}$', start):
            start_time = datetime.datetime.strptime(start, "%d/%m/%Y %H:%M")        # 23/06/2022 12:10
        elif re.match(r'\d{2}\/\d{2} \d{2}:\d{2}$', start):
            now = datetime.datetime.now()
            start_time = datetime.datetime.strptime(start, "%d/%m %H:%M")           # 23/06 12:10
            start_time = start_time.replace(year=now.year)
        elif re.match(r'\d{2}:\d{2}$', start):
            now = datetime.datetime.now()
            start_time = datetime.datetime.strptime(start, "%H:%M")                 # 12:10
            start_time = start_time.replace(year=now.year, month=now.month, day=now.day)
        else:
            print('Format of start time is not recognized: {}'.format(start))
            exit(1)
    return start_time


def duration_format(duration):
    if re.match(r'\d+d\d+h\d+m$', duration):
        r = re.match(r'(\d+)d(\d+)h(\d+)m$', duration)
        duration_days, duration_hours, duration_mins = r.groups()
        duration_hours = '{:0>2}'.format(duration_hours)
        duration_mins = '{:0>2}'.format(duration_mins)
    elif re.match(r'\d+h\d+m$', duration):
        r = re.match(r'(\d+)h(\d+)m$', duration)
        duration_hours, duration_mins = r.groups()
        duration_days = '0'
        duration_hours = '{:0>2}'.format(duration_hours)
        duration_mins = '{:0>2}'.format(duration_mins)
    elif re.match(r'\d+h$', duration):
        r = re.match(r'(\d+)h$', duration)
        duration_hours = r.group(1)
        duration_days = '0'
        duration_hours = '{:0>2}'.format(duration_hours)
        duration_mins = '00'
    elif re.match(r'\d+m$', duration):
        r = re.match(r'(\d+)m$', duration)
        duration_mins = r.group(1)
        duration_days = '0'
        duration_hours = '00'
        duration_mins = '{:0>2}'.format(duration_mins)
    else:
        print('Format of duration is not recognized: {}'.format(duration))
        exit(1)
    return duration_days, duration_hours, duration_mins


def create_maint_window(routers, uid, maint_name, start_time, duration_days, duration_hours, duration_mins,
                        org_name, org_type):
    dm_router = routers['DevMgmt']
    params = {
        "uid": uid,
        "id": "",
        "name": maint_name,
        "startDate": start_time.strftime("%m/%d/%Y"),
        "startHours": start_time.strftime("%H"),
        "startMinutes": start_time.strftime("%M"),
        "timezone": "Europe/Brussels",
        "durationDays": duration_days,
        "durationHours": duration_hours,
        "durationMinutes": duration_mins,
        "repeat": "Never",
        "startProductionState": 300,
        "enabled": True,
        }
    response = dm_router.callMethod('addMaintWindow', params=params)
    if not response['result']['success']:
        print('Could not create maintenance window {} - Message: {}'.format(name, response['result']['msg']))
        exit(1)
    else:
        print('Created maintenance window {} on {} {}.'.format(maint_name, org_type, org_name))


def clean_maint_windows(routers, uid, org_name, org_type):
    dm_router = routers['DevMgmt']
    response = dm_router.callMethod('getMaintWindows', uid=uid)
    if not response['result']['success']:
        print("Could not fetch the current maintenance windows for {} {}.".format(org_type, org_name))
        exit(1)
    now = int(time.time())
    for maint_window in response['result']['data']:
        if not maint_window['enabled']:
            continue
        if maint_window['repeat'] != 'Never':
            continue
        if re.match(r'((\d*)\sdays\s)?(\d\d):(\d\d):(\d\d)', maint_window['duration']):
            r_duration = re.match(r'((\d*)\sdays\s)?(\d\d):(\d\d):(\d\d)', maint_window['duration'])
            duration_s = (int(r_duration.group(2)) if r_duration.group(2) else 0) * 86400 + \
                         int(r_duration.group(3)) * 3600 + int(r_duration.group(4)) * 60
            duration_days = r_duration.group(2)
            duration_hours = r_duration.group(3)
            duration_mins = r_duration.group(4)
        elif re.match(r'(\d\d):(\d\d)', maint_window['duration']):
            r_duration = re.match(r'(\d\d):(\d\d)', maint_window['duration'])
            duration_s = int(r_duration.group(1)) * 3600 + int(r_duration.group(2)) * 60
            duration_days = '00'
            duration_hours = r_duration.group(1)
            duration_mins = r_duration.group(2)
        else:
            print('Could not read duration from "{}" in group {}.'.format(maint_window['duration'], group))
            exit(1)
        # TODO: maybe easier with timedelta ??
        end = int(maint_window['start']) + duration_s
        if end < now:
            r_start = re.match(r'(\d{4})\/(\d{2})\/(\d{2})\s(\d{2}):(\d{2}):\d{2} (.*)', maint_window['startTime'])
            if not r_start:
                print('Could not read start time from "{}" in group {}.'.format(maint_window['startTime'], group))
                exit(1)
            params = {
                "uid": uid,
                "id": maint_window['id'],
                "startDate": "{}/{}/{}".format(r_start.group(2), r_start.group(3), r_start.group(1)),
                "startHours": r_start.group(4),
                "startMinutes": r_start.group(5),
                "timezone": maint_window['timezone'],
                "durationDays": duration_days,
                "durationHours": duration_hours,
                "durationMinutes": duration_mins,
                "repeat": maint_window['repeat'],
                "startProductionState": maint_window['startProdState'],
                "enabled": False
                }
            response = dm_router.callMethod('editMaintWindow', params=params)
            if not response['result']['success']:
                print('Could not disable maintenance window {} on {}} {}.'.format(maint_window['name'], org_type,
                                                                                  org_name))
            else:
                print('Disabled maintenance window {} on {} {}.'.format(maint_window['name'], org_type, org_name))

# TODO: The following functions should be merged, the differences are small
def maint_components(routers, path, maint_name, start, duration):
    uid = '/zport/dmd/ComponentGroups{}'.format(path)
    # Check presence of organizer
    check_org_exists(routers, uid, path, 'component group')

    # Check for old maintenance windows and disable them
    clean_maint_windows(routers, uid, path, 'component group')

    # Create start data
    start_time = start_format(start)

    # Create duration data
    duration_days, duration_hours, duration_mins = duration_format(duration)

    # Add new maintenance window
    create_maint_window(routers, uid, maint_name, start_time, duration_days, duration_hours, duration_mins,
                        path, 'component_group')
    return


def maint_group(routers, group, name, start, duration):
    group_uid = '/zport/dmd/Groups{}'.format(group)
    # Check presence of organizer
    check_org_exists(routers, group_uid, group, 'group')

    # Check for old maintenance windows and disable them
    clean_maint_windows(routers, group_uid, group, 'group')

    # Create start data
    start_time = start_format(start)

    # Create duration data
    duration_days, duration_hours, duration_mins = duration_format(duration)

    # Add new maintenance window
    create_maint_window(routers, group_uid, name, start_time, duration_days, duration_hours, duration_mins,
                        group, 'group')
    return


def maint_system(routers, system, name, start, duration):
    system_uid = '/zport/dmd/Systems{}'.format(system)

    # Check presence of organizer
    check_org_exists(routers, system_uid, system, 'system')

    # Check for old maintenance windows and disable them
    clean_maint_windows(routers, system_uid, system, 'system')

    # Create start data
    start_time = start_format(start)

    # Create duration data
    duration_days, duration_hours, duration_mins = duration_format(duration)

    # Add new maintenance window
    create_maint_window(routers, system_uid, name, start_time, duration_days, duration_hours, duration_mins,
                        system, 'system')
    return


def maint_device(routers, device, maint_name, start, duration):
    d_router = routers['Device']
    if device.startswith('/'):
        org_uid = '/zport/dmd/Devices{}'.format(device)
    else:
        response = d_router.callMethod('getDevices', params={'name': device})
        if not response['result']['success']:
            print('Could not find device {}.'.format(device))
            print(response)
            exit(1)
        elif response['result']['totalCount'] > 1:
            print('The device hostname should be refined. {} devices have been found.'.format(
                response['result']['totalCount']))
        else:
            org_uid = response['result']['devices'][0]['uid']

    # Check presence of organizer
    check_org_exists(routers, org_uid, device, 'device')

    # Check for old maintenance windows and disable them
    clean_maint_windows(routers, org_uid, device, 'device')

    # Create start data
    start_time = start_format(start)

    # Create duration data
    duration_days, duration_hours, duration_mins = duration_format(duration)

    # Add new maintenance window
    create_maint_window(routers, org_uid, maint_name, start_time, duration_days, duration_hours, duration_mins,
                        device, 'device')
    return


context_defs = {
    'components': maint_components,
    'groups': maint_group,
    'systems': maint_system,
    'devices': maint_device,
}

def maintenance(routers, context, name, start, duration):
    now = int(time.time())
    # TODO: in try
    apps = yaml.safe_load(file(APP_FILE, 'r'))
    if 'Applications' not in apps:
        print('Wrong format of application file')
        exit(1)
    apps = apps['Applications']

    if context not in apps:
        print('Context {} not found in applications file.'.format(context))
        exit(1)
    for organizer, org_func in context_defs.items():
        if organizer not in apps[context]:
            continue
        for leaf in apps[context][organizer]:
            org_func(routers, leaf, name, start, duration)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Set maintenance on device')
    parser.add_argument('-s', dest='section', action='store', default='z6_test')
    parser.add_argument('-c', dest='context', action='store')
    parser.add_argument('-n', dest='name', action='store', default='maintenance')
    parser.add_argument('-f', dest='start', action='store', default='now')
    parser.add_argument('-d', dest='duration', action='store', default='2h')

    # TODO: validate maintenance name, as there are restrictions on the characters
    # TODO: provide a file with instructions on maint windows to apply
    # TODO: in yaml file, add default values for start and duration, per context
    # TODO: Switch to a GUI (PySimpleGUI ?)
    options = parser.parse_args()
    section = options.section
    context = options.context
    if not context:
        print('No context defined.')
        exit(1)
    name = options.name
    start = options.start
    duration = options.duration

    # Routers
    routers = {}
    routers['DevMgmt'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='DeviceManagementRouter')
    routers['Device'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='DeviceRouter')
    maintenance(routers, context, name, start, duration)

