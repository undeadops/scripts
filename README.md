scripts
=======

Various Scripts I've written for various tasks..


Backups
====
- backupMySQL2s3.py: Make a backup of mysql databases and push to S3 for storage
- s3GpgDbbackup-v2.py: Retake on the above, adding GPG encryption to backed up file... 
- sync2S3.py: Kinda like an Rsync of a directory to S3, uses boto to mirror a local directory into S3.

Juniper
====
- junos-portLastFlapped.py: Quick script to look at port state changes on Juniper EX switches
- junos-sessions.py: Quick, crude script to assist in finding bittorrenters(lots of ports open...) from a J-Series router at a clients site

Nagios
====
- check-piston-status.py: Quick Nagios check for Piston Cloud Cluster Status
