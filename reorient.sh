#!/bin/bash

if [ $# -eq 0 ]
  then
    echo "No arguments supplied, please use file path as an argument"
    exit
fi

filepath=$1

cd $filepath/NIMS_data

for folder in `ls .`
	do pushd $folder
		for file in `ls *.nii.gz` 
			do 
				echo $file
				`fslreorient2std $file $file`
			done
		popd
	done


