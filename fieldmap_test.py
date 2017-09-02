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
import os.path.join as opj # Helper function

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

#Figure out what bids info xlsx is named 
project_file_contents = os.listdir(project_filepath)
BIDS_filename = [x for x in project_file_contents if "BIDS_info" in x]
print(BIDS_filename)

xls = pd.ExcelFile(opj(project_filepath, BIDS_filename[0]))

# Parse fieldmap input
fieldmap = xls.parse('fieldmap', convert_float=False)
fieldmap.intended_for = fieldmap.intended_for.split()

print(fieldmap)