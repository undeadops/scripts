#!/usr/bin/env python

__author__ = 'Mitch Anderson'
__date__ = '08-14-2011'
__version__ = '1.0'

"""
Releasing Under the New BSD License same as where I got some of the code from.

Most of the S3 directory sync code came from the django-command-extensions project
on Google Code: http://code.google.com/p/django-command-extensions/wiki/sync_media_s3

I just added a more generic wrapper and the delete portions.
"""

import datetime
import os
import sys
import time
import getopt
import mimetypes
import email

# Make sure boto is available
try:
    import boto
    import boto.exception
except ImportError:
    raise ImportError, "The boto Python library is not installed."

class S3Sync:
	def __init__(self, verbose=True, force=False, quiet=False, delete=True, **kwargs):
		self.SYNC_DIR = kwargs['S3_SYNC_DIR']
		self.AWS_BUCKET_NAME = kwargs['S3_BUCKET']
		self.AWS_ACCESS_KEY_ID = kwargs['KEY']
		self.AWS_SECRET_ACCESS_KEY = kwargs['SECRET']
		self.FILTER_LIST = ['.DS_Store','.svn','.idea',]

		self.verbosity = verbose
		self.quiet = quiet
		self.delete = delete
		self.do_force = force
		self.do_gzip = False
		self.do_expires = True
		self.upload_count = 0
		self.skip_count = 0
		self.del_count = 0
		self.prefix = ""

	def sync_s3(self):
		"""
		Walks sync directory and uploads to S3
		"""
		bucket, key = self.open_s3()
		os.path.walk(self.SYNC_DIR, self.upload_s3,
			(bucket, key, self.AWS_BUCKET_NAME, self.SYNC_DIR))

	def del_s3(self):
		"""
		Removes Files from S3 that are not on the local file system
		"""
		bucket, key = self.open_s3()
		s3list = bucket.list()
		root_dir, prefix = self.SYNC_DIR.rsplit('/', 1 )
		for k in s3list:
			if not os.path.isfile(os.path.join(root_dir, k.name)):
				if self.verbosity:
					print "Deleting %s..." % (k.name)
				bucket.delete_key(k.name)
				self.del_count += 1

	def open_s3(self):
		"""
		Opens connection to S3 returning bucket and key
		"""
		conn = boto.connect_s3(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY)
		try:
			bucket = conn.get_bucket(self.AWS_BUCKET_NAME)
		except boto.exception.S3ResponseError:
			bucket = conn.create_bucket(self.AWS_BUCKET_NAME)
		return bucket, boto.s3.key.Key(bucket)

	def upload_s3(self, arg, dirname, names):
		"""
		This is the callback to os.path.walk and where much of the work happens
		"""
		bucket, key, bucket_name, root_dir = arg # expand arg tuple

		if not root_dir.endswith('/'):
			self.prefix = root_dir.split('/')[-1]
			root_dir = root_dir + '/'

		for file in names:
			headers = {}

			if file in self.FILTER_LIST:
				continue # Skip files we don't want to sync

			filename = os.path.join(dirname, file)
			if os.path.isdir(filename):
				continue # Don't uplaod directories

			breakout = 0
			for f in self.FILTER_LIST:
				if f in filename:
					breakout = 1 # Don't upload anything relating to filter_list
			if breakout:
				continue

			file_key = filename[len(root_dir):]
			if self.prefix:
				file_key = "%s/%s" % (self.prefix, file_key)

			# Check if file on S3 is older than local file, if so, upload
			if not self.do_force:
				s3_key = bucket.get_key(file_key)
				if s3_key:
					s3_datetime = datetime.datetime(*time.strptime(
						s3_key.last_modified, '%a, %d %b %Y %H:%M:%S %Z')[0:6])
					local_datetime = datetime.datetime.utcfromtimestamp(
						os.stat(filename).st_mtime)
					if local_datetime < s3_datetime:
						self.skip_count += 1
						if self.verbosity > 1:
							print "File %s hasn't been modified since last " \
								"being uploaded" % (file_key)
						continue

			# File is newer, let's process and upload
			if self.verbosity > 0:
				print "Uploading %s..." % (file_key)

			content_type = mimetypes.guess_type(filename)[0]
			if content_type:
				headers['Content_Type'] = content_type

			file_obj = open(filename, 'rb')
			file_size = os.fstat(file_obj.fileno()).st_size
			filedata = file_obj.read()
			if self.do_gzip:
				# Gzipping only if file is large enough (>1K is recommended)
				# and only if file is a common text type (not a binary file)
				if file_size > 1024 and content_type in self.GZIP_CONTENT_TYPES:
					filedata = self.compress_string(filedata)
					headers['Content-Encoding'] = 'gzip'
				if self.verbosity > 1:
					print "\tgzipped: %dk to %dk" % \
						(file_size/1024, len(filedata)/1024)
			if self.do_expires:
				# HTTP/1.0
				headers['Expires'] = '%s GMT' % (email.Utils.formatdate(
					time.mktime((datetime.datetime.now() +
					datetime.timedelta(days=365*2)).timetuple())))
				# HTTP/1.1
				headers['Cache-Control'] = 'max-age %d' % (3600 * 24 * 365 * 2)
				if self.verbosity > 1:
					print "\texpires: %s" % (headers['Expires'])
					print "\tcache-control: %s" % (headers['Cache-Control'])

			try:
				key.name = file_key
				key.set_contents_from_string(filedata, headers, replace=True)
				key.make_public()
			except boto.s3.connection.S3CreateError, e:
				print "Failed: %s" % e
			except Exception, e:
				print e
				raise
			else:
				self.upload_count += 1

			file_obj.close()

	def run(self):
		# upload all files found.
		self.sync_s3()
		if self.delete:
			self.del_s3()
		if not self.quiet:
			print "%d files uploaded." % (self.upload_count)
			print "%d files skipped." % (self.skip_count)
		if not self.quiet and self.delete:
			print "%d files deleted." % (self.del_count)

def main(argv):
	AWS_KEY = None
	AWS_SECRET = None
	verbose = False
	force = False
	quiet = False
	delete = False
	# Parse Options
	try:
		opt, args = getopt.getopt(argv, "hd:b:K:S:vfdq", ["help", "directory=", "bucket=", "key=", "secret=", 'verbose', 'force', 'delete', 'quiet',])
	except getopt.GetoptError, err:
		print str(err)
		usage()
		sys.exit(2)
	for o, a in opt:
		if o in ("-h", "--help"):
			usage()
			sys.exit()
		elif o in ("-d", "--directory"):
			SYNC_DIR = a
		elif o in ("-b", "--bucket"):
			BUCKET = a
		elif o in ("-K", "--key"):
			AWS_KEY = a
		elif o in ("-S", "--secret"):
			AWS_SECRET = a
		elif o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-f", "--force"):
			force = True
		elif o in ("-d", "--delete"):
			delete = True
		elif o in ("-q", "--queit"):
			quiet = True
		else:
			assert False, "unhandled option"

	# Check for AWS Keys
	if not AWS_KEY:
		AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
	if not AWS_SECRET:
		AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")

	if not AWS_KEY or not AWS_SECRET:
		print "Missing AWS Keys"
		print usage()
		sys.exit(2)
	# Start processing
	mys3 = S3Sync(verbose, force, quiet, delete, S3_SYNC_DIR=SYNC_DIR, S3_BUCKET=BUCKET, KEY=AWS_KEY, SECRET=AWS_SECRET)
	mys3.run()

def usage():
	usage = """
	-h --help		Prints this
	-d --directory		Directory To Sync to S3
	-b --bucket		S3 Bucket to sync to
	-K --key		AWS Access Key
	-S --secret		AWS Secret Access Key
	-v --verbose		Verbose Output
	-f --force		Force upload of Everything regardless of age
	-d --delete		Delete S3 if file is not local
	-q --quiet		No File totals, completly quiet

	AWS Keys can be in environment variables as well under:
	AWS_ACCESS_KEY_ID = <access key>
	AWS_SECRET_ACCESS_KEY = <secret access key>
	"""
	print usage


if __name__ == '__main__':
	main(sys.argv[1:])

