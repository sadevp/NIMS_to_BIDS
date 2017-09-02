from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

# coding: utf-8

# In[ ]:

from builtins import input
from builtins import open
from builtins import str
from future import standard_library
standard_library.install_aliases()
print("Importing Libraries...\n")

import pandas as pd
import os
import re
from shutil import copyfile
import json
import sys
import subprocess
import pdb # Debugging
import glob
from os.path import join as opj # Helper function

home_dir = os.environ['PI_HOME']


#Get Data Filepath
if (len(sys.argv) == 2):
    project_dir = str(sys.argv[1]).strip(' ')
else:
    #"Data needs to be in format: \n       Project Filename            \n        /          \\              \n    NIMS_data  BIDS_info.xlsx      \n       /                           \nSub1 Sub2 Sub3                     \n\n                                   \n
    print("NIMS_to_BIDS.py can take the project's file path as an argument\nNo argument detected\nPlease drag in file path from folder")
    project_dir = input().strip(' ')

project_filepath = opj(home_dir, project_dir)

#path variables
BIDS= opj(project_filepath, 'BIDS_data')
NIMS= opj(project_filepath, 'NIMS_data')

#Read files

#Figure out what bids info xlsx is named 
project_file_contents = os.listdir(project_filepath)
BIDS_filename = [x for x in project_file_contents if "BIDS_info" in x]
print(BIDS_filename)

#Make sure there's only one bids file
assert len(BIDS_filename) == 1, 'This folder does not have a BIDS_info file or it has more than one info file' 

xls = pd.ExcelFile(project_filepath + "/" + BIDS_filename[0])

#Make folder if folder doesn't exist function
def makefolder(name):
    if not os.path.exists(name):
        os.makedirs(name)
        
#Load and Clean XLS File
participants = xls.parse('participants')
participants.participant_id = participants.participant_id.astype('str')

protocol = xls.parse('protocol', convert_float=False).iloc[1:,:6] #columns 5 on are reference columns
protocol = protocol.dropna(axis=0, thresh=3) #get rid of items that don't have a bids equivalent
protocol.run_number = protocol.run_number.astype('str').str.strip('.0').str.zfill(2) #Convert run int to string

fieldmap = xls.parse('fieldmap', convert_float=False)
fieldmap.intended_for = [str(s) for s in fieldmap.intended_for]
fieldmap.intended_for = [s.split() for s in fieldmap.intended_for]

#Create "bold" portion of filename
protocol['bold_filename'] = ''
protocol.loc[protocol['ANAT_or_FUNC'] == 'func', 'bold_filename'] = '_bold'

#Concatanate filepath and clean
protocol["BIDS_scan_title_path"] = BIDS + "sub-###/" + protocol.ANAT_or_FUNC + "/sub-###_" + protocol.BIDS_scan_title + "_run-" + protocol.run_number + protocol.bold_filename + ".nii.gz"
protocol.BIDS_scan_title_path = protocol.BIDS_scan_title_path.str.replace('_run-nan', '') #For items that don't have runs

#Create list for NIMS -> bids conversion
NIMS_protocol_filenames = protocol.NIMS_scan_title.tolist() #Convert protocol scan titles to list
NIMS_BIDS_conversion = protocol[["NIMS_scan_title","BIDS_scan_title_path"]]

def check_against_protocol(participants,protocol): 
    
    all_files_correct = True
    
    for index, row in participants.iterrows():

    	NIMS_participant = opj(NIMS, row.nims_title)
    	NIMS_participant_subdirs = [opj(NIMS_participant, d) for d in os.listdir(NIMS_participant)]
    	NIMS_participant_subdirs = [d for d in NIMS_participant_subdirs if os.path.isdir(d)]

        for item in set(NIMS_protocol_filenames):
            protocol_dirs = [d for d in NIMS_participant_subdirs if item in d]
            protocol_files = []
            for d in protocol_dirs:
                protocol_search = glob.glob(opj(d, "*.nii.gz"))
                protocol_files.append(protocol_search[0])

            print(protocol_files)


        # #If directory is there, try will work
        # try:
        #     #Get all files in participant directory
        #     NIMS_participant_directories = opj(NIMS, row.nims_title)
        #     NIMS_participant_filenames = opj(NIMS, row.nims_title)
           
        #     #Delete all non-nii.gz files
        #     NIMS_participant_filenames = [x for x in NIMS_participant_filenames if ".nii.gz"  in x]


        #     for item in set(NIMS_protocol_filenames):
                
        #         directory_filenames = [x for x in NIMS_participant_filenames if item in x]
        #         protocol_filenames = NIMS_BIDS_conversion[NIMS_BIDS_conversion.NIMS_scan_title.str.contains(item)]
        #         protocol_filenames = protocol_filenames.iloc[:,1].tolist()

        #         if len(directory_filenames) < len(protocol_filenames):
        #             print('{} : sub-{} : << {} {} files in folder {} files in protocol\n'.                    format(str(row.nims_title), str(row.participant_id), item.rjust(20), len(directory_filenames), len(protocol_filenames)))

        #         elif len(directory_filenames) > len(protocol_filenames):
        #             print('{} : sub-{} : >> {} {} files in folder {} files in protocol\n'.                    format(str(row.nims_title), str(row.participant_id), item.rjust(20), len(directory_filenames), len(protocol_filenames)))
        #             all_files_correct = False
                    
        #         elif len(directory_filenames) == len(protocol_filenames):
        #             print('{} : sub-{} : == {} {} files in folder {} files in protocol\n'.                    format(str(row.nims_title), str(row.participant_id), item.rjust(20), len(directory_filenames), len(protocol_filenames)))

        #     print("------------")
        
        # except:
        #     all_files_correct = False
        #     print("sub-" + str(row.participant_id) + " : -- ERROR - folder is missing \n------------")

        
        
        
    # if all_files_correct:
    #     print("\nAll your folders match your protocol\n")  
    # else:
    #     print("\nSome folders do not match your protocol, please resolve errors\n")
    
    # return all_files_correct

check_against_protocol(participants, protocol)
