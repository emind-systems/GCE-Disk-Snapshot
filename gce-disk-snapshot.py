#!/usr/bin/env python

## Usage:
# gce-disk-snapshot.py [-h] -d DISK -z ZONE [-H HISTORY] [-s STATDIR]
#
# GCE Disk Snapshot Maker
# 
# optional arguments:
#   -h, --help                         show this help message and exit
#   -d DISK, --disk DISK               Disk name
#   -z ZONE, --zone ZONE               The GCE zone of the disk to be imaged
#   -H HISTORY, --history HISTORY      Number of historic snapshots to keep
#   -s STATDIR, --statdir STATDIR      Directory where to write the status file
#

import os
import sh
import sys
import time
import syslog
import argparse
import subprocess

# GLOBAL VARIABLES

# Variables related to the script itself
script = os.path.realpath(__file__)
script_name = os.path.splitext(os.path.basename(script))[0]
script_ext = os.path.splitext(os.path.basename(script))[1]
script_path = os.path.dirname(script)

# Generic variables
disk_name=''
gce_zone=''
historic_snapshots=30
status_dir='/var/run/emind/gce-ds'
status_filename=''
last_error='Successful execution.'

# SHELL commands
gcloud = sh.Command('gcloud', ['/usr/bin','/usr/local/bin'])

# CONSTANTS
RESULT_OK = 0
RESULT_ERR = 1

def set_last_error(error_msg):
  global last_error
  last_error = error_msg

def write_log(msg,msg_type=syslog.LOG_INFO):
  try:
    print msg
    syslog.syslog(msg_type, msg)
  except Exception as ex:
    print 'Logging exception: %s' % ex

def cleanup_old_snapshots(snap_name):
  # gcloud compute snapshots list -r ^prod-1-media-content-1a.* --uri
  write_log('Performing cleanup ...')
  try:
    result = gcloud('compute','snapshots', 'list', '-r', '^' + snap_name + '-[0-9]{6}.*', '--uri')
  except Exception as ex:
    set_last_error('GCloud execution error: %s' % ex.stderr)
    write_log(last_error,syslog.LOG_ERR)
    return RESULT_ERR
  # Extract exactly the name of the snapshots
  snapshot_list = result.stdout.strip().split('\n')
  for iIndex in range(len(snapshot_list)):
    snapshot_list[iIndex] = os.path.splitext(os.path.basename(snapshot_list[iIndex]))[0]
  snapshot_list.sort(key=str.lower)
  # Do the cleanup
  while len(snapshot_list) > historic_snapshots:
    write_log('Removing snapshot "'+snapshot_list[0]+'" ...')
    try:
      result = gcloud('compute','snapshots', 'delete', '--quiet', snapshot_list[0])
    except Exception as ex:
      set_last_error('GCloud execution error: %s' % ex.stderr)
      write_log(last_error,syslog.LOG_ERR)
      return RESULT_ERR
    del snapshot_list[0]
  return RESULT_OK
  # print snapshot_list

def create_snapshot(disk_name,gc_zone):
  write_log('Creating snapshot for disk "'+disk_name+'" ...')
  snapshot_name = disk_name + '-' + time.strftime('%Y%m%d-%H%M')
  try:
    result = gcloud('compute', 'disks', 'snapshot', disk_name, '--snapshot-names', snapshot_name, '--zone', gc_zone)
    write_log('Snapshot created: ' + snapshot_name)
  except Exception as ex:
    set_last_error('GCloud execution error: %s' % ex.stderr)
    write_log(last_error,syslog.LOG_ERR)
    return RESULT_ERR
  return RESULT_OK

def get_gce_zones():
  zone_list = None
  result = None
  try:
    result = gcloud('compute', 'zones', 'list', '--uri')
  except Exception as ex:
    set_last_error('GCloud execution error: %s' % ex.stderr)
    write_log(last_error,syslog.LOG_ERR)
  if result is not None:
    zone_list = result.stdout.strip().split('\n')
    for iIndex in range(len(zone_list)):
      zone_list[iIndex] = os.path.splitext(os.path.basename(zone_list[iIndex]))[0]
  return zone_list

def save_status_file(filename, status):
  try:
    status_lines = []
    status_lines.append('TIMESTAMP=' + str(long(time.time())))
    status_lines.append('STATUS=' + str(status))
    status_lines.append('LAST_ERROR=' + last_error.replace('\n','\t'))
    with open(filename, 'w') as status_file:
      for aLine in status_lines:
        status_file.write(aLine + '\n')
  except Exception as ex:
    write_log('Exception while saving the status file: %s' % ex, syslog.LOG_ERR)

# Command line arguments
parser = argparse.ArgumentParser(description='GCE Disk Snapshot Maker')
parser.add_argument('-d', '--disk', help='Disk name', required=True)
parser.add_argument('-z', '--zone', help='The GCE zone of the disk to be imaged', required=True)
parser.add_argument('-H', '--history', help='Number of historic snapshots to keep', required=False, default=historic_snapshots, type=int)
parser.add_argument('-s', '--statdir', help='Directory where to write the status file', required=False, default=status_dir)

args = vars(parser.parse_args())

disk_name = args['disk']
gce_zone = args['zone']
historic_snapshots = args['history']
status_dir = args['statdir']
status_filename = status_dir+'/'+disk_name+'.status'

# Check status directory
try:
  if not(os.path.isdir(status_dir)):
    os.makedirs(status_dir)
except Exception as ex:
  set_last_error('Error accessing the status directory: %s' % ex)
  write_log(last_error, syslog.LOG_ERR)
  sys.exit(RESULT_ERR)

available_zones = get_gce_zones()
if gce_zone not in available_zones:
  set_last_error('The zone "'+gce_zone+'" does not exist.')
  write_log(last_error,syslog.LOG_ERR)
  save_status_file(status_filename,RESULT_ERR)
  sys.exit(RESULT_ERR)

result = create_snapshot(disk_name, gce_zone)
if result == RESULT_OK:
  result = cleanup_old_snapshots(disk_name)

save_status_file(status_filename,result)

sys.exit(result)
