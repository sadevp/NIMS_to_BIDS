
# coding: utf-8

# # NIMS-to-BIDS converter v.2
# Written by Natalia Vélez, 9/17
# 
# Changes in this version:
# 
# * Change to file structure: raw data are now stored in `$PI_SCRATCH`
# * Incorporate changes to protocol file, including tracking sequence numbers 
# * Add support for fieldmaps
# * Remove redundancies in the code
# 
# Load dependencies:

# In[32]:


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from builtins import input
from builtins import open
from builtins import str
from future import standard_library
standard_library.install_aliases()
print("Importing Libraries...\n")

import warnings
import datetime
import numpy as np
import pandas as pd
import os
import re
from shutil import copyfile
import json
import sys
import subprocess
import glob
from os.path import join as opj # Helper function


# Set input and output directories:

# In[33]:


home_dir = os.environ['PI_HOME']
scratch_dir = os.environ['PI_SCRATCH']

#project_name =  str(sys.argv[1]).strip(' ') # Uncomment for production
project_name = 'SwiSt'
project_dir = opj(home_dir, project_name)
NIMS = opj(scratch_dir, project_name, 'NIMS_data')
BIDS = opj(project_dir, 'BIDS_data')
BIDS_file = glob.glob(opj(project_dir, '*BIDS_info*.xlsx'))

#Make sure there's only one bids file
assert len(BIDS_file) == 1, 'This folder does not have a BIDS_info file or it has more than one info file' 
xls = pd.ExcelFile(BIDS_file[0])

# Create a new text file to report outputs
report_dir = opj(project_dir, 'reports')
report_tstamp = '{:%Y%m%d_%H%M}'.format(datetime.datetime.now())
report_path = opj(report_dir, 'NIMS2BIDS_%s_%s_report.txt' % (project_name, report_tstamp))
copyjob_path = opj(report_dir, 'NIMS2BIDS_%s_%s_copyjob.csv' % (project_name, report_tstamp))
report_file = open(report_path, 'w')

# Write to report
if not os.path.exists(report_dir):
    os.makedirs(report_dir)

def report_print(msg):
    report_file.write(msg + '\n')
    print(msg)
    
# Write to report
print('Creating report at: %s' % report_path)
report_file.write('=== NIMS TO BIDS CONVERSION ===\n')
report_file.write('Timestamp: {:%Y-%m-%d %H:%M:%S}\n'.format(datetime.datetime.now()))
report_print('Input: %s' % NIMS)
report_print('Output: %s' % BIDS)
print('BIDS_info file: %s' % BIDS_file[0])
report_file.write('BIDS_info file: %s \n \n -----' % BIDS_file[0])


# Load participant information:

# In[45]:


participants = xls.parse('participants')
participants.participant_id = ['sub-%02d' % int(n) for n in participants.participant_id]
participants.head()


# Load task data:

# In[35]:


tasks = xls.parse('tasks').iloc[1:,]
tasks.head()


# Load protocol data:

# In[36]:


protocol = xls.parse('protocol', convert_float=False).iloc[1:,]
protocol = protocol[~pd.isnull(protocol.sequence_type)] # Remove columns with missing BIDS data types
protocol.head()


# Find input (NIMS-formatted) files and specify output (BIDS-formatted) files:

# In[37]:


report_file.write('Assembling copy job:')
session_IDs = participants.nims_title
participant_IDs = participants.participant_id
custom_protocols = np.unique(protocol.nims_title)
custom_protocols = custom_protocols[custom_protocols != 'default']
copy_job_cols = ['session', 'in_img', 'out_img', 'out_info', 'out_info_file']
copy_job = pd.DataFrame(columns = copy_job_cols)

# Helper function: Searches for matching input files
def input_path(row, session_id):
    d = row.to_dict()
    
    # Templates: Build search string based on sequence number and type
    input_fname = '*fieldmap.nii.gz' if d['sequence_type'] == 'fmap' else '*_1.nii.gz'
    input_template = opj(NIMS, session_id, '*_%i_1_%s', input_fname)
    input_search = input_template % (d['sequence_no'], d['NIMS_scan_title'])
    
    # Matches: Find matching sequences
    input_matches = glob.glob(input_search)    
    path = input_matches[0] if input_matches else np.nan
    if not input_matches:
        report_print('Missing file: %s' % input_search)
        
    return path
    
# Helper function: Builds path for output files
def output_path(row, participant_id):
    d = row.to_dict()
    output_run = '_run-%02d' % d['run_number'] if ~np.isnan(d['run_number']) else ''
    output_bold = '_bold' if d['sequence_type'] == 'func' else ''
    output_filename = '%s_%s%s%s.nii.gz' % (participant_id, d['BIDS_scan_title'], output_run, output_bold)
    output_path = opj(BIDS, participant_id, d['sequence_type'], output_filename)
    
    return output_path
    
# Helper function: Prepares JSON file keys
def output_keys(row, participant_id, session_protocol):
    # Fields common to all sequences
    standard_fields = ['nims_title', 'sequence_no', 'NIMS_scan_title',
                       'BIDS_scan_title', 'run_number', 'sequence_type']
    
    # Remove standard fields and NA'sfrom row 
    # (only custom fields related to the current sequence remain)
    row = row.drop(standard_fields)
    row = row.dropna()
    row_dict = row.to_dict()
    
    # If dictionary contains an IntendedFor field (for fieldmaps), replace the sequence numbers
    # with BIDS-formatted filenames
    if 'IntendedFor' in row_dict:
        # Subject directory
        subj_dir = opj(BIDS, participant_id)
        
        if isinstance(row_dict['IntendedFor'], str):
            target_runs_raw = row_dict['IntendedFor'].split(' ')
            target_runs = [int(r) for r in target_runs_raw]
        else:
            target_runs = [int(row_dict['IntendedFor'])]
        target_protocol = session_protocol[session_protocol['sequence_no'].isin(target_runs)]

        # Get BIDS output for each file
        get_target_path = lambda row: output_path(row, participant_id)
        get_rel_path = lambda path: os.path.relpath(path, subj_dir)
        target_full_path = target_protocol.apply(get_target_path, axis = 1)
        target_full_path = target_full_path.tolist()
        target_path = [get_rel_path(path) for path in target_full_path]
        
        # Replace IntendedFor with properly formatted paths
        row_dict['IntendedFor'] = target_path
        
    # Convert row_dict to JSON string
    row_json = json.dumps(row_dict) if row_dict else np.nan
    return row_json
    
# Iterate over participants and assemble copy job:
for session, participant_id in zip(session_IDs, participant_IDs):
    #participant_id = participants[participants.nims_title == session]['participant_id']
    
    # Get correct protocol
    is_custom = session in custom_protocols
    protocol_type = 'CUSTOM' if is_custom else 'DEFAULT'
    protocol_ref = session if is_custom else 'default'
    session_protocol = protocol[protocol.nims_title == protocol_ref]
    
    # Assemble copy_job
    input_files = session_protocol.apply(lambda row: input_path(row, session), axis=1)
    output_files = session_protocol.apply(lambda row: output_path(row, participant_id), axis=1)
    output_info = session_protocol.apply(lambda row: output_keys(row, participant_id, session_protocol), axis=1)
    output_info_files = [f.replace('.nii.gz', '.json') for f in output_files]
    output_info_files = [f if isinstance(info, str) else np.nan for f,info in zip(output_info_files, output_info)]
    session_col = [session for _ in range(len(input_files))]
    
    # Convert to list
    input_files = input_files.tolist()
    output_files = output_files.tolist()
    output_info = output_info.tolist()
    
    tmp_items = list(zip(copy_job_cols, [session_col, input_files, output_files, output_info, output_info_files]))
    tmp_copy = pd.DataFrame.from_items(tmp_items)
    copy_job = copy_job.append(tmp_copy)
    
# Save copy job to reports
copy_job.to_csv(copyjob_path)

# Raise an error if files are missing
if np.any(pd.isnull(copy_job['in_img'])):
    report_file.write('Conversion not successful: Missing files\n')
    raise Exception('ERROR: Missing files found. Please consult report for details.')
else:
    copyjob_msg = 'Copy-job successfully assembled! Details at: %s' % copyjob_path
    print(copyjob_msg)
    report_file.write(copyjob_msg)


# The variable `copy_job` contains a dataframe with: input images (`in_img`), output images (`out_img`), output metadata (`out_info`), metadata path (`out_info_file`).

# In[38]:


copy_job.head()


# Now that all files have been found, let's make all of the necessary folders:

# In[39]:


data_types = np.unique(protocol['sequence_type'].tolist())
sub_dirs = [opj(BIDS, sub) for sub in participant_IDs]
data_dirs = [opj(s, d) for d in data_types for s in sub_dirs]
new_dirs = sub_dirs + data_dirs

report_print('New directories created:')
for d in new_dirs:
    if not os.path.exists(d):
        report_print(d)
        os.makedirs(d)
report_file.write('\n')


# Copy over the files:

# In[40]:


report_print('Copying files...')
for idx, row in copy_job.iterrows():
    report_file.write('Input: %s\n' % row['in_img'])
    report_file.write('Output: %s \n \n' % row['out_img'])
    copyfile(row['in_img'], row['out_img'])
    #os.system('fslreorient2std %s %s' % (row['out_img'], row['out_img']))


# Create metadata:

# In[21]:


def write_file(contents, path):
    with open(path, 'w') as openfile:
        openfile.write(contents)

copy_metadata = copy_job.dropna()
for row in copy_metadata.iterrows():
    write_file(row[1]['out_info'], row[1]['out_info_file'])


# Copy dataset, participant, and task information:

# In[68]:


# Dataset
dataset_file = opj(BIDS, 'dataset_description.json')
dataset_description = json.dumps({"BIDSVersion": "1.0.0", "License": ""})
write_file(dataset_description, dataset_file)

# Participants
participant_file = opj(BIDS, 'participants.tsv')
participant_description = participants.copy()
participant_description = participant_description.drop('nims_title', axis = 1)
participant_description.to_csv(participant_file)

# Tasks
for task in tasks.iterrows():
    task_dict = task[1].to_dict()
    del task_dict['BIDS_scan_title']
    
    task_fname = opj(BIDS, '%s.json' % task[1]['BIDS_scan_title'])
    task_data = json.dumps(task_dict)
    write_file(task_data, task_fname)
    
report_print('Done!')

