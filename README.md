# NIMS_to_BIDS Conversion

## Summary

Takes neuroimaging downloaded from the Neurobiological Image Managament System at Stanford University (https://cni.stanford.edu/nims/) and converts it to BIDS (http://bids.neuroimaging.io/)

## Usage

python NIMS_to_BIDS.py /path/to/directory



```
NIMS Data Format (e.g)

|-- ProjectFilename
    |-- BIDS_info.xlsx
    |-- NIMS_data
        |-- 20170101_14000
            |-- 0001_01_3Plane_Loc_fgre.nii.gz
            |-- 0003_01_ASSET_calibration.nii.gz
            |-- 0005_01_BOLD_EPI_29mm_2sec.nii.gz
            |-- 0006_01_BOLD_EPI_29mm_2sec.nii.gz
            |-- 0007_01_BOLD_EPI_29mm_2sec.nii.gz
            |-- 0008_01_BOLD_EPI_29mm_2sec.nii.gz
            |-- 0009_01_T1w_9mm_BRAVO.nii.gz  

BIDS Data Format (e.g) http://bids.neuroimaging.io/

|-- ProjectFilename
    |-- BIDS_data
        |-- participants.tsv
        |-- task-empathy_bold.json
        |-- dataset_description.json
        |-- sub-101
            |-- anat
                |-- sub-101_T1w.nii.gz
            |-- func
                |-- sub-101_task-empathy_run-01_bold.nii.gz
                |-- sub-101_task-empathy_run-02_bold.nii.gz
                |-- sub-101_task-empathy_run-03_bold.nii.gz
                |-- sub-101_task-empathy_run-04_bold.nii.gz
```



NIMS_to_BIDS uses a BIDS_info.xlsx file as a reference between NIMS and BIDS formatting. 

Participant information requires: 
  * nims_title (the data and a 5 digit id number)
  * participant_id
  * sex
  * age
    
Protocol information requires
  * NIMS_scan_title 
  	*e.g. 3Plane_Loc_fgre
  * BIDS_scan_title 
  	*following the bids naming convention, if you would not like this to go to your bids folder, leave blank
  * full_task_name 
  	*e.g. "balloonanalogrisktask" to "balloon analog risk task"
  * run_number 
  	*if applicable, if not, leave blank
  * repetion_time 
  	*if applicable, if not, leave blank
  
 Once the BIDS_info document is filled out, running the script will prompt you for:
  * file path to project folder
 
The script will:
  * check to see if all your participant folders are in NIMS_data
  * check to see if your scans match your protocol
  * create BIDS_data file, renaming volume files and creating .json and .tsv files
