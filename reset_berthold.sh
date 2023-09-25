#!/bin/bash
if [[ -n $(find /mnt/berthold/latest -type f -mmin +2) ]]
then
        echo "no change for 2 minutes in /mnt/berthold/latest"
        if [[ $(</mnt/berthold/latest) != "-1" ]]; then
                echo "value not negative, setting it negative"
                echo "-1" > /mnt/berthold/latest
        fi
fi
