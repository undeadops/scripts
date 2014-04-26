#!/usr/bin/env python
##
## Mitch Anderson - May 17th 2010
## This takes the session output from a JunOS firewall/router
## and counts the number of NAT's an IP address has... and then prints
## that number along with the souce ports and destination IP/port
## 
## Reason I wrote this was to help find people using bittorrent...
## since bittorrent normally will use lots of high source and destination
## ports... anyone with a large amount of these... will most likely be 
## torrenting

## This information is gathered by logging into the router and running:
## show security flow session interface reth5.0 node primary
##
## This script logs into the router with the provided username/password
##

import re,sys,getpass,getopt

mesg = """ This script depends on python-paramiko please install it...."""

try:
	import ssh
except:
	print mesg
	sys.exit(1)


def calculate_IP_nats(contents):
	'''Return a dictionary with the IP as the index'''
	ipaddr = {}
	# match source and destination ip's... they're different because the destination
	# has a protocol matched up with it
	psrc = re.compile("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d+)")
	pdst = re.compile("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d+);([a-z]+)\,")
	for line in contents:
		if re.search('In:', line):
			(v1, src, v2, dest, v3, v4) = line.split()
			msrc = psrc.match(src)
			mdst = pdst.match(dest)
			try:
				ipaddr[msrc.group(1)].append([msrc.group(2),mdst.group(1),mdst.group(2),mdst.group(3)])
			except:
				ipaddr[msrc.group(1)] = []
				ipaddr[msrc.group(1)].append([msrc.group(2),mdst.group(1),mdst.group(2),mdst.group(3)])
	return ipaddr


def main(outfile=None):
	# get router information
	router = raw_input("Router to connect to: ")
	username = raw_input("Username [%s]: " % getpass.getuser())
	if username == None:
		username = getpass.getuser()
	password = getpass.getpass("Password: ")

	# connect to router
	try:
		s = ssh.Connection(host = router, username = username, password = password)
	except:
		print "There was an error connecting to %s." % router
		sys.exit(2)
	# grab our list and get out
	contents = s.execute('show security flow session interface reth5.0 node primary')
	s.close()

	# process and write the output to a variable
	ipaddrs = calculate_IP_nats(contents)
	output = str()
	for i, d in ipaddrs.iteritems():
		output += i + " - " + str(len(d)) + " connections" + "\n"
		if len(d) > 60:
			for c in d:
				output += "\t [" + c[0] + "] --> " + c[1] + " [" + c[2] + "]" + "\n"
	
	# Check to see if we are to write the output to a file
	# or the screen
	if outfile:	
		try:	
			f = open(outfile, 'w')
		except:
			print "Error... couldn't write to %s" % outfile
			sys.exit(3)

		f.write(output)
		f.close()
	else:
		print output
	


if __name__ == '__main__':
	try:
		opts, args = getopt.getopt(sys.argv[1:], "f:", ["file="])
	except getopt.GetoptError, err:
		print str(err)
		sys.exit(1)

	for o, a in opts:
		if o in ("-f", "--file"):
			outfile = a
	
	try:
		main(outfile)
	except:
		main()


