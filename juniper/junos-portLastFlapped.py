#!/usr/bin/env python
##
## Mitch Anderson - May 17th 2010
## This script logs into a Juniper EX Switch, lists out ports, greps for downed
## ports, and then checks each to see how long they've been in a down state.
##
## This script logs into the switch with the provided username/password
##

import re,sys,getpass,getopt

mesg = """ This script depends on python-paramiko please install it...."""

try:
	import ssh
except:
	print mesg
	sys.exit(1)

def getLastFlapped(port,sshconn):
	'''Return the Date and Time of the Last time the port flapped'''
	lastflapped = sshconn.execute('show interfaces %s | grep Last' % port)[0]
	lastflapped = lastflapped.split(':',1)[1]
	return lastflapped.strip()


def main(outfile=None):
	# get switch information
	switch = raw_input("Switch to connect to: ")
	username = raw_input("Username [%s]: " % getpass.getuser())
	if username == None:
		username = getpass.getuser()
	password = getpass.getpass("Password: ")

	# connect to switch
	try:
		s = ssh.Connection(host = switch, username = username, password = password)
	except:
		print "There was an error connecting to %s." % switch
		sys.exit(2)

	portList = []
	# grab our list and get out
	output = s.execute('show interfaces terse | grep down | except \.0 | grep ge-')
	for port in output:
		port = port.strip()
		if port == '': continue
		p = port.split()[0]
		portList.append({'port': p, 'lastflapped': getLastFlapped(p, s)})
	s.close()

	# process and write the output to a variable
	display = "Ports currently down on switch %s:  \n" % switch
	for p in portList:
		display = display + " %s\t: %s\n" % (p['port'],p['lastflapped'])
	
	# Check to see if we are to write the output to a file
	# or the screen
	if outfile:	
		try:	
			f = open(outfile, 'w')
		except:
			print "Error... couldn't write to %s" % outfile
			sys.exit(3)

		f.write(display)
		f.close()
	else:
		print display
	


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


