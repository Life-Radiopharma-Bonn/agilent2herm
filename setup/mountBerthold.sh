#!/bin/bash
/usr/sbin/modprobe -q ftdi_sio
sleep 1
echo 0403 b5f6 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id
sleep 1
systemctl stop herm
sleep 1
systemctl start herm
