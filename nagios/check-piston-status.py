#!/usr/bin/env python

import sys, getopt, ast
from fabric.api import run, env, settings, hide
from fabric.tasks import execute

def check_status():
    with settings(
            hide('warnings', 'running', 'stdout', 'stderr', 'everything')
        ):
        status = ast.literal_eval(run('piston-dev.py cluster-info -s'))

    # TODO: Status checker needs to look through returned json problem server
    if status['control']['state'] == 'optimal':
        print "OK: Piston Cluster Optimal"
        sys.exit(0)
    else:
        print "Warning: Piston Cluster Error State"
        sys.exit(1)



def main(argv):
    env.user = 'admin'
    env.disable_known_hosts = True
    env.no_keys = True
    # Disable Output
    env.debug = False
    try:
        opts, args = getopt.getopt(argv,"hH:p:",["hostname=","password="])
    except getopt.GetoptError:
        print 'check-piston-status.py -H <hostname> -p <password>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print 'check-piston-status.py -H <hostname> -p <password>'
            sys.exit()
        if opt in ('-H', "--hostname"):
            env.hosts = [arg]
        elif opt in ("-p", "--password"):
            env.password = arg
    with settings(
        hide('warnings', 'running', 'stdout', 'stderr', 'everything')
        ):
        execute(check_status)


if __name__ == '__main__':
    main(sys.argv[1:])