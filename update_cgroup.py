import zenAPI.zenApiLib
import argparse
import datetime
import re
import time
import yaml


def update_cg(routers, cgroup, name):
    device_router = routers['Device']
    cgroup_router = routers['CGroup']
    search_router = routers['Search']

    # TODO: check presence of component group
    uid = '/zport/dmd/ComponentGroups{}'.format(cgroup)

    response = device_router.callMethod("getInfo", uid=uid)
    print(response)
    print('-' * 80)
    response = cgroup_router.callMethod("getComponents", uid=uid)
    print(response)

    # searchRouter -> getCategoryCounts
    print('-' * 80)
    response = search_router.callMethod("getCategoryCounts", query=name)
    print(response)

    # searchRouter -> getAllResults
    print('-' * 80)
    response = search_router.callMethod("getAllResults", query=name)
    print(response)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Set maintenance on device')
    parser.add_argument('-s', dest='section', action='store', default='z6_test')
    parser.add_argument('-c', dest='cgroup', action='store')
    parser.add_argument('-k', dest='name', action='store')

    options = parser.parse_args()
    section = options.section
    cgroup = options.cgroup
    if not cgroup:
        print('No Component Group defined.')
        exit(1)
    name = options.name

    # Routers
    routers = {}
    routers['DevMgmt'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='DeviceManagementRouter')
    routers['Device'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='DeviceRouter')
    routers['CGroup'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='ComponentGroupRouter')
    routers['Search'] = zenAPI.zenApiLib.zenConnector(section=section, routerName='SearchRouter')
    update_cg(routers, cgroup, name)

