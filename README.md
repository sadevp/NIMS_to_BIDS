# NIMS_to_BIDS Conversion

## Summary

Takes neuroimaging downloaded from the Neurobiological Image Managament System at Stanford University (https://cni.stanford.edu/nims/) and converts it to BIDS (http://bids.neuroimaging.io/)

Data will need to be in legacy format from the NIMS website

## Usage

python NIMS_to_BIDS.py projectName

This version of NIMS-to-BIDS is intended to work through the command line on Sherlock. The script takes a single argument---the project name---and searches for scans in $PI_SCRATCH/[projectName]/NIMS_data. It then places the BIDS-formatted data in $PI_HOME/[projectName]/BIDS_data.

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

**dataset**: Dataset information
Following BIDS convention for `dataset_information.json`
Required field: Name (database name)
Optional fields: License, authors, Acknowledgments, HowToAcknowledge, Funding, ReferencesAndLinks, DatasetDOI

**tasks**: Task information

* BIDS_scan_title
  * If you would not like a scan to be included in your BIDS folder, leave blank
  * For task-related fMRI, start the scan name with "task-" (e.g., task-tomloc)
* TaskName
  * e.g., "Theory of Mind functional localizer" for "tomloc"
* RepetitionTime
* EchoTime
  * Used for fieldmap correction. If not applicable, leave blank

**participants**: Participant information

  * nims_title (the data and a 5 digit id number)
  * participant_id
  * Optional: age, gender

**protocol**: Protocol information

**Required fields:**
* NIMS_title
  * The session title. "default" for default protocol (see notes below), specific session IDs for custom protocols.
* sequence_no
  * The number of the sequence, according to the BIDS protocol. Must correspond to folder number in NIMS_data.
  * TODO: In this current version, you must specify sequence numbers even for the default protocol. That means that you must specify custom protocols for participants if their sequence numbers are off by a constant shift, even if the sequences are in the same order as the default protocol. (For example, if you run two shim sequences for one subject, rather than one, then the part of the protocol we're copying to BIDS will start at sequence #5, not sequence #4. In the current version, you'd need to specify a custom protocol for this subject. In future versions, this may not be necessary.)
* NIMS_scan_title
  *e.g. 3Plane_Loc_fgre
* BIDS_scan_title 
  * Following the bids naming convention. If you would not like this to go to your bids folder, leave blank
  * By convention: use "fieldmap" for fieldmaps, "task-[TASKNAME]" for functional tasks (even resting state fMRI, in which case you would use "task-rest"), and modality (e.g., "T1w") for structural images.
  * Make sure that task-based fMRI names match BIDS_scan_title in "tasks"
* run_number
  *if applicable, if not, leave blank
* sequence type
  * Data type. Use BIDS convention (e.g., "anat", "func", "fmap")

**A note on sequence-specific fields:**
The protocol sheet is totally customizable. If you add new columns to the protocol sheet, the script will use it to add custom meta-data to sequences that have a non-blank value. In the example BIDS_info sheet, there are two such custom fields, "Units" and "IntendedFor", which are used specifically for fieldmap sequences. If no changes are made to the script, these will be saved "as-is" as meta-data. For example, it will create a JSON file specifically for the sequence in line 6 that contains the following information:

```
{"Units": "Hz",
 "IntendedFor": "5 6"}
```

(Note that some changes have been made to the script so that "IntendedFor" instead converts the sequence numbers ("5 6") to relative paths to the correct BOLD images, as shown in the BIDS specification.)

This means that, in principle, you can add *any* new meta-data to the protocols, as long as: (1) the column name matches a field in the BIDS specification, and (2) the content of the cell can be saved to a JSON file as is. Some additional changes will need to be made if you need to transform the input (e.g., the sequence numbers in "IntendedFor") to conform to the BIDS specification.

The script will:
  * check to see if all your participant folders are in NIMS_data folder
  * check to see if your scans match your protocol
  * create BIDS_data file, renaming volume files and creating .json and .tsv files