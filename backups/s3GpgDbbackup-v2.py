#!/usr/bin/env python
author__ = 'Mitch Anderson'
__date__ = '06-14-2011'
__version__ = '0.1'

import datetime, os, sys
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import gnupg

#####################################
DATE=datetime.date.today().strftime("%Y%m%d")
OLDDATE=(datetime.date.today() + datetime.timedelta(days=-28)).strftime("%Y%m%d")
YESTERDAY=(datetime.date.today() + datetime.timedelta(days=-1)).strftime("%Y%m%d")
#####################################
NAME="sqlserver"
SQLHOST="localhost"
SQLUSER="root"
SQLPASS="password"

BACKUPDIR="/var/backups"

####
# Access Keys
#
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
BUCKET=''

if os.access(BACKUPDIR, os.F_OK):
    if os.access(BACKUPDIR, os.W_OK):
        os.chdir(BACKUPDIR)
    else:
        print "%s is not writable" % BACKUPDIR
        sys.exit(2)
else:
    print "%s does not exist" % BACKUPDIR
    sys.exit(2)

newname="backups-mysql-%s-%s.sql.gz" % (NAME,DATE)
oldname="backups-mysql-%s-%s.sql.gz" % (NAME,OLDDATE)
yesterdayname="backups-mysql-%s-%s.sql.gz" % (NAME,YESTERDAY)


newfile="%s/%s" % (BACKUPDIR, newname)

print "Creating %s" % newname
command = "/usr/bin/mysqldump -u%s -p%s -h %s --all-databases | /bin/gzip --best > %s" % (SQLUSER,SQLPASS,SQLHOST,newfile)
os.system(command)


gpg = gnupg.GPG(gnupghome='/home/my/gpghome')
with open(newfile, 'rb') as f:
    status = gpg.encrypt_file(
        f, recipients=['me@email.com'],
        output='%s.gpg' % newfile )

print 'ok: ', status.ok
print 'status: ', status.status
print 'stderr: ', status.stderr


print "Uploading %s" % newname
conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
bucket = conn.get_bucket(BUCKET)
k = Key(bucket)
k.key = "mysql/" + newname
print BACKUPDIR + "/" + newname
k.set_contents_from_filename( "%s" % (BACKUPDIR + "/" + newname) )
k.set_acl('private')

print "Cleaning Local: %s" % yesterdayname
try:
    if os.path.isfile(yesterdayname):
        os.unlink(yesterdayname)
except Exception, e:
    print e

print "Deleting Old: %s" % oldname
dk = Key(bucket)
dk.key = "mysql/" + oldname
try:
    if dk.exists():
        dk.delete()
except Exception, e:
    print e
print "Done!"

