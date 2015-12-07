GCE-Disk-Snapshot
=================

 Usage:
--------

gce-disk-snapshot.py [-h] -d DISK -z ZONE [-H HISTORY] [-s STATDIR]

GCE Disk Snapshot Maker

optional arguments:
  -h, --help                         show this help message and exit
  -d DISK, --disk DISK               Disk name
  -z ZONE, --zone ZONE               The GCE zone of the disk to be imaged
  -H HISTORY, --history HISTORY      Number of historic snapshots to keep
  -s STATDIR, --statdir STATDIR      Directory where to write the status file

License
-------

See the [LICENSE](LICENSE.md) file for license rights and limitations.