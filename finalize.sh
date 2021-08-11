#!/bin/bash

dest="/home/steven/public_html/files/update.tar.gz"
exclude="--exclude=staging --exclude=compile --exclude=go.vim --exclude=config.json "
buildroot_dirs="buildroot-2020.02.9"

[ -f "$dest" ] && rm -v "$dest"

while [[ ! -z "$1" ]] ; do
   case $1 in
      '--no-data')
         exclude+="--exclude=data "
         echo No data will be backed up.
         ;;

      '--no-tools')
         exclude+="--exclude tools "
         echo No binary tools or helper scripts will be backed up.
         ;;

      '--no-buildroot')
         for dir in $buildroot_dirs ; do
            exclude+="--exclude=$dir "
         done
         echo No Buildroot source trees or filesystems will be backed up.
         ;;

      '--backup')
         mount | grep work-storage 2>&1 >> /dev/null || {
            echo Network attached storage was not detected.
            exit 1
         }
         name="$(date +%Y-%m-%d_%H-%M-%S)_build-master.tar.gz"
         dest="/mnt/work-storage/Steven/$name"
         ;;
   esac
   shift
done

command="tar czf $dest $exclude ."

echo "Exclusions: $exclude"
echo "Final command: $command"
echo "Running..."
$command
echo "Done!"

