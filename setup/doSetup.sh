#!/bin/bash
pip3 install pyserial inotify --break-system-packages
cp 99-usbftdi.rules /etc/udev/rules.d/99-usbftdi.rules
mkdir /lrp

cp mountBerthold.sh /etc/mountBerthold.sh
chmod +x /etc/mountBerthold.sh

cp ../reset_berthold.sh /lrp/reset_berthold.sh
chmod +x /lrp/set_berthold.sh

mkdir /mnt/berthold
echo "tmpfs /mnt/berthold	tmpfs	defaults,size=20M	0	0" >> /etc/fstab
mount -a

cp ../telnetserver.service /etc/systemd/system/telnetserver.service
cp ../herm.service /etc/systemd/system/herm.service
cp ../instrument.service /etc/systemd/system/instrument.service
systemctl daemon-reload


cp ../instrumentcommunication.py /lrp/instrument.py
cp ../telnetserver.py /lrp/telnetserver.py
cp ../herm.py /lrp/herm.py

systemctl enable telnetserver
systemctl enable herm
systemctl enable instrument

cat <(crontab -l) <(echo "* * * * * /lrp/reset_berthold.sh") | crontab -
