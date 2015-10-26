#!/usr/bin/env python

import sys
import os
from os.path import expanduser
import boto3
import argparse


class Ec2SecGroups:
    def __init__(self, args):
        """
        Grab All Security Groups and Rules, Store, comapre/alert based on changes
        """

        self.file_active_secgroups = expanduser('~') + "/.aws-secgroups.active"
        self.file_pending_secgroups = expanduser('~') + "/.aws-secgroups.pending"

        self.changes = {}

        if args.commit_changes:
            self._move_pending()
        else:
            # Connect to AWS
            self.ec2 = boto3.client('ec2')
            # Store Current EC2 Security Groups
            self.current_secgroups = []
            # Collect Security Groups and Rules
            self._pull_current_security_groups()
            # Compare Results with Currently Known Active
            self._compare()

        if args.check:
            print self._print_changes()

        if args.nagios:
            self._check_nagios()


    def _pull_current_security_groups(self):
        """
        Gather All Security Groups and rules, save to list
        """
        secgroups = self.ec2.describe_security_groups()
        
        for sg in secgroups['SecurityGroups']:
            for rule in sg['IpPermissions']:
                if rule['IpProtocol'] != '-1':
                    r = "[%s]%s %s:%s,%s " % (sg['GroupId'],sg['GroupName'],rule['IpProtocol'],rule['ToPort'],rule['FromPort'])
                else:
                    r = "[%s]%s %s " % (sg['GroupId'],sg['GroupName'],'ALL')
                if len(rule['IpRanges']) > 0:
                    for ip in rule['IpRanges']:
                        self.current_secgroups.append(r+'cidr:'+ip['CidrIp'])
                if len(rule['UserIdGroupPairs']) > 0:
                    for g in rule['UserIdGroupPairs']:
                        try:
                            self.current_secgroups.append(r+'groups:'+g['GroupId']+"-"+g['GroupName'])
                        except KeyError:
                            self.current_secgroups.append(r+'groups:'+g['GroupId']+"-UNKNOWN")
        # Write Out Pending SecGroups
        self._write_secgroups(self.file_pending_secgroups)


    def _write_secgroups(self, filename):
        """
        Write Current self._output to Active File
        """
        try:
            os.remove(filename)
        except OSError:
            pass
        fh = open(filename, "w")
        security_groups = sorted(self.current_secgroups)
        for line in security_groups:
            fh.write(line + "\n")
        fh.close()


    def _compare(self):
        """
        Compare Latest with Known active
        """
        acked_secgroups = []

        try:
            for f in open(self.file_active_secgroups).readlines():
                # Remove newline characters from lines read in
                acked_secgroups.append(f.strip())

        except (OSError, IOError) as e:
            print "WARNING: Active Security Groups file did not exist, creating..."
            self._write_secgroups(self.file_active_secgroups)
            sys.exit(0)
        
        additions = []
        subtractions = []

        # Need to look for additions/subtractions from active list and current
        for a in self.current_secgroups:
            if a not in acked_secgroups:
                additions.append(a)

        for s in acked_secgroups:
            if s not in self.current_secgroups:
                subtractions.append(s)

        # Create dict/list
        self.changes = {'additions': additions, 'removed': subtractions }


    def _check_nagios(self):
        """
        Output meant for a Nagios Check
        """
        num_additions = len(self.changes['additions'])
        num_removes = len(self.changes['removed'])
        if num_additions > 0 or num_removes > 0:
            retcode = 1
            text_out = 'WARNING: AWS Security Group Changes|add=%s,rem=%s\n' % (num_additions, num_removes)
            text_out += self._print_changes()
        else:
            retcode = 0
            text_out = 'OK: No Changes|add=0,rem=0\n'

        print text_out
        sys.exit(retcode)
        

    def _print_changes(self):
        """
        Simple output for displaying whats changed
        """
        output = "\n"
        if len(self.changes['additions']) > 0:
            output += 'Additions: \n'
            for a in self.changes['additions']:
                output += "+ %s\n" % a
            output += "----------\n"
        elif len(self.changes['removed']) > 0:
            output += 'Removed: \n'
            for r in self.changes['removed']:
                output += "- %s\n" % r
        else:
            output += "NO CHANGES"
        output += "\n"
        return output

    def _move_pending(self):
        print "Commiting Changes from pending..."
        os.remove(self.file_active_secgroups)
        print ".."
        os.rename(self.file_pending_secgroups, self.file_active_secgroups)
        print "done!"


def main():
    argp = argparse.ArgumentParser(prog='check-security-groups.py', usage='%(prog)s [options]')
    argp.add_argument('--nagios', action="store_true", help='Run Script with Output for a Nagios Check')
    argp.add_argument('--check', action="store_true", help="Run Script, Display Current Differences")
    argp.add_argument('--commit-changes', action="store_true", help='Confirm Pending Changes to Active')
    args = argp.parse_args()
    
    sgs = Ec2SecGroups(args)
    


if __name__ == '__main__':
    main()