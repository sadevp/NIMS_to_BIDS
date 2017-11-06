
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

# In[68]:


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


# Helper functions:

# In[69]:


# Open and write to file
def write_file(contents, path):
    with open(path, 'wb') as openfile:
        openfile.write(contents)
        
# Make directory (if it doesn't already exist)
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def copyif(source, target):
    if not os.path.isfile(target):
        copyfile(source, target)

# Open and write to JSON file
def write_json(data, path):
    json_data = json.dumps(data)
    write_file(json_data, path)
    
# Replaces basename in path (ignoring text in the path name)
# e.g. IN: replace_basename('fieldmap_path/fieldmap.nii.gz', 'fieldmap', 'magnitude') 
# OUT: 'fieldmap_path/magnitude.nii.gz'
def replace_basename(series, oldstr, newstr):
    d = series.apply(os.path.dirname)
    f = series.apply(os.path.basename)
    f = f.str.replace(oldstr, newstr)
    
    df = pd.DataFrame(dict(d = d, f = f))
    new_path_fun = lambda row: opj(row['d'], row['f'])
    new_paths = df.apply(new_path_fun, axis = 1).tolist()
        
    return new_paths

# Assembles BIDS filename
def assemble_bids_filename(d, custom_keys = None):
    default_keys = ['participant', 'ses', 'task', 'acq', 'run', 'echo', 'filetype']
    key_order = default_keys if custom_keys is None else custom_keys
    
    filename_parts = [d[k] for k in key_order if k in d.keys()]
    filename_base = '_'.join(filename_parts)
    filename = filename_base + '.nii.gz'
    
    return filename


# Set input and output directories:

# In[70]:


home_dir = os.environ['PI_HOME']
scratch_dir = os.environ['SCRATCH']

project_name =  str(sys.argv[1]).strip(' ') # Uncomment for production
project_dir = opj(home_dir, project_name)
report_dir = opj(project_dir, 'reports')
NIMS = opj(scratch_dir, project_name, 'NIMS_data_anonymized')
if os.path.exists(NIMS):
    print('Using anonymized data')
else:
    print('Warning! Using non-anonymized data')
    NIMS = NIMS.replace('_anonymized', '')

BIDS = opj(project_dir, 'BIDS_data')
BIDS_file = glob.glob(opj(project_dir, '*BIDS_info*.xlsx'))

#Make sure there's only one bids file
assert len(BIDS_file) == 1, 'This folder does not have a BIDS_info file or it has more than one info file' 
xls = pd.ExcelFile(BIDS_file[0])

# Write to report
mkdir(report_dir)
mkdir(BIDS)

# Create a new text file to report outputs
report_tstamp = '{:%Y%m%d_%H%M}'.format(datetime.datetime.now())
report_path = opj(report_dir, 'NIMS2BIDS_%s_%s_report.txt' % (project_name, report_tstamp))
copyjob_path = opj(report_dir, 'NIMS2BIDS_%s_%s_copyjob.csv' % (project_name, report_tstamp))
report_file = open(report_path, 'w')

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


# Load dataset description:

# In[71]:


dataset = xls.parse('dataset').iloc[1,:]
dataset = dataset.dropna() # Remove blank fields
dataset_data = {'Name': 'Dataset', 'BIDSVersion': '1.0.0'} # Default, required arguments
dataset_custom = dataset.to_dict()
dataset_data.update(dataset_custom) # Override defaults

# Format authors as array
if 'Authors' in dataset_data:
    dataset_data['Authors'] = dataset_data['Authors'].split(',')

# Save to file
dataset_file = opj(BIDS, 'dataset_description.json')
write_json(dataset_data, dataset_file)

# Load participant information:

# In[72]:


participants = xls.parse('participants')

try:
    participants.participant_id = ['sub-%02d' % int(n) for n in participants.participant_id]
except ValueError:
    participants.participant_id = ['sub-%s' % p for p in participants.participant_id]

# Save to file
participants_file = opj(BIDS, 'participants.tsv')
participants.to_csv(participants_file, index = False, sep = b'\t')


# Load task data:

# In[73]:


tasks = xls.parse('tasks').iloc[1:,]

# Save tasks to file
for task in tasks.iterrows():
    task_dict = task[1].to_dict()
    del task_dict['BIDS_scan_title']
    
    task_fname = opj(BIDS, '%s_bold.json' % task[1]['BIDS_scan_title'])
    write_json(task_dict, task_fname)


# Load protocol data:

# In[74]:


protocol = xls.parse('protocol', convert_float=False).iloc[1:,]
protocol = protocol[~pd.isnull(protocol.sequence_type)] # Remove columns with missing BIDS data types
participant_ids = list(protocol.participant_id)

for p in range(len(participant_ids)):
    try:
        participant_ids[p] = 'sub-%02d' % participant_ids[p]
    except TypeError:
        pass
    
protocol['participant_id'] = participant_ids


# Find input (NIMS-formatted) files and specify output (BIDS-formatted) files:

# In[75]:


report_file.write('Assembling copy job:')

# Get participant and session IDs
session_IDs = list(participants.nims_title)
participant_IDs = list(participants.participant_id)
session_dict = dict(zip(participant_IDs, session_IDs))

# Identify custom protocols
custom_protocols = np.unique(list(protocol.participant_id))
custom_protocols = custom_protocols[custom_protocols != 'default']
print('Using custom protocols for sessions: %s' % custom_protocols)

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
    filetypes = {'func': 'bold', 'fmap': 'fieldmap'}
    out_d = {
        'participant': participant_id,
        'task': None if pd.isnull(d['BIDS_scan_title']) else d['BIDS_scan_title'],
        'run': 'run-%02d' % d['run_number'] if ~np.isnan(d['run_number']) else None,
        'filetype': filetypes[d['sequence_type']] if d['sequence_type'] in filetypes.keys() else None}
    out_d = {k:v for k,v in out_d.items() if v is not None}
    
    out_file = assemble_bids_filename(out_d)
    out_path = opj(BIDS, participant_id, d['sequence_type'], out_file)
    
    return out_path
    
# Helper function: Prepares JSON file keys
def output_keys(row, participant_id, session_protocol):
    # Fields common to all sequences
    standard_fields = ['participant_id', 'sequence_no', 'NIMS_scan_title',
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
for (participant_id, session) in zip(participant_IDs, session_IDs):
    #participant_id = participants[participants.nims_title == session]['participant_id']
    
    # Get correct protocol
    is_custom = participant_id in custom_protocols
    protocol_type = 'CUSTOM' if is_custom else 'DEFAULT'
    protocol_ref = participant_id if is_custom else 'default'
    session_protocol = protocol[protocol.participant_id == protocol_ref]
    
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
    
    # Add magnitude images to fieldmaps
    mag_images = copy_job[copy_job['out_img'].str.contains('fmap')].copy()
    mag_images['in_img'] = replace_basename(mag_images['in_img'], 'fieldmap', '')
    mag_images['out_img'] = replace_basename(mag_images['out_img'], 'fieldmap', 'magnitude')

    mag_images['out_info'] = np.nan
    mag_images['out_info_file'] = np.nan
    copy_job = copy_job.append(mag_images)
    
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

# Now that all files have been found, let's make all of the necessary folders:

# In[9]:


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

# In[10]:


report_print('Copying files...')
for idx, row in copy_job.iterrows():
    report_file.write('Input: %s\n' % row['in_img'])
    report_file.write('Output: %s \n \n' % row['out_img'])
    copyif(row['in_img'], row['out_img'])
    #os.system('fslreorient2std %s %s' % (row['out_img'], row['out_img']))


# Create metadata:

# In[11]:


copy_metadata = copy_job.dropna()
for row in copy_metadata.iterrows():
    write_file(row[1]['out_info'], row[1]['out_info_file'])
    
report_print('Done! Unpacking successful.')

