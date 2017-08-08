
# coding: utf-8

# In[1]:

from __future__ import with_statement
from __future__ import absolute_import
import pandas as pd
import os
import re
from shutil import copyfile
import json
from io import open


# In[5]:

#Get Data Filepath

print u"Data needs to be in format: \n       Project Filename            \n        /          \\              \n    NIMS_data  BIDS_info.xlsx      \n       /                           \nSub1 Sub2 Sub3                     \n\n                                   \nPlease drag in project filepath    \n"
      
project_filepath = raw_input()

      
#path variables
BIDS= project_filepath + u'/BIDS_data/'
NIMS= project_filepath + u'/NIMS_data/'


# In[11]:

#Read files

#Figure out what bids info xlsx is named 
project_file_contents = os.listdir(project_filepath)
BIDS_filename = [x for x in project_file_contents if u"BIDS_info" in x]



assert len(BIDS_filename) == 1, u'This folder does not have a BIDS_info file or it has more than one info file' 
xls = pd.ExcelFile(project_filepath + u"/" + BIDS_filename[0])


#Make folder if folder doesn't exist function
def makefolder(name):
    if not os.path.exists(name):
        os.makedirs(name)


# In[12]:

#Load and Clean XLS File
participants = xls.parse(u'participants')

protocol = xls.parse(u'protocol', convert_float=False).iloc[1:,:6] #columns 5 on are reference columns
protocol = protocol.dropna(axis=0, thresh=3) #get rid of items that don't have a bids equivalent
protocol.run_number = protocol.run_number.astype(u'str').unicode.strip(u'.0').unicode.zfill(2) #Convert run int to string


#Create "bold" portion of filename
protocol[u'bold_filename'] = u''
protocol.loc[protocol[u'ANAT_or_FUNC'] == u'func', u'bold_filename'] = u'_bold'

#Concatanate filename and clean
protocol[u"BIDS_scan_title_path"] = BIDS + u"sub-###/" + protocol.ANAT_or_FUNC + u"/sub-###_" + protocol.BIDS_scan_title + u"_run-" + protocol.run_number + protocol.bold_filename + u".nii.gz"
protocol.BIDS_scan_title_path = protocol.BIDS_scan_title_path.unicode.replace(u'_run-nan', u'') #For items that don't have runs

#Create list for NIMS -> bids conversion
NIMS_protocol_filenames = protocol.NIMS_scan_title.tolist() #Convert protocol scan titles to list
NIMS_BIDS_conversion = protocol[[u"NIMS_scan_title",u"BIDS_scan_title_path"]]


# In[13]:

def check_against_protocol(participants,protocol): 
    
    all_files_correct = True

    for index, row in participants.iterrows():
        
        #If directory is there, try will work
        try:
            #Get all files in participant directory
            NIMS_participant_filenames = os.listdir(NIMS + row.nims_title)
            #Delete all non-nii.gz files
            NIMS_participant_filenames = [x for x in NIMS_participant_filenames if u".nii.gz"  in x]

            for item in set(NIMS_protocol_filenames):
                
                directory_filenames = [x for x in NIMS_participant_filenames if item in x]
                protocol_filenames = NIMS_BIDS_conversion[NIMS_BIDS_conversion.NIMS_scan_title.unicode.contains(item)]
                protocol_filenames = protocol_filenames.iloc[:,1].tolist()

                if len(directory_filenames) == len(protocol_filenames):
                    print u"sub-" + unicode(row.participant_id) + u": ++ " + item.rjust(20) + u" match"

                else:
                    print u"sub-" + unicode(row.participant_id) + u": -- "+ item.rjust(20) + u" files do not match protocol"
                    all_files_correct = False
            print u"------------"
        
        except:
            all_files_correct = False
            print u"sub-" + unicode(row.participant_id) + u": ERROR - folder is missing \n------"

        
        
        
    print u'\nAll your folders match your protocol\n' if all_files_correct else print u'\nSome folders do not match your protocol, please resolve errors\n'
    
    return all_files_correct


# In[14]:

def write_text_files(participants, protocol): 
    
    def to_file(filename, content): 
        with open(BIDS + filename + u".json", u"w") as text_file:
            text_file.write(content)
    
    #Data Description
    dataset_description = json.dumps({u"BIDSVersion": u"1.0.0",                                    u"License": u"",                                    u"Name": u"dummy task name",                                   u"ReferencesAndLinks": u""})
    to_file(u"dataset_description", dataset_description)
    

    #Task Description
    for item in set(protocol.loc[protocol.ANAT_or_FUNC == u"func", u'BIDS_scan_title']):
        full_task_name = protocol.loc[protocol.BIDS_scan_title == item, u'full_task_name']
        full_task_name = full_task_name.reset_index(drop=True)[0] #Gets first instance of RT
        
        repetition_time = protocol.loc[protocol.BIDS_scan_title == item, u'repetition_time']
        repetition_time = repetition_time.reset_index(drop=True)[0] #Gets first instance of RT
        task_json = json.dumps({u"RepetitionTime": repetition_time, u"TaskName" : full_task_name})

        to_file(item + u"_bold", task_json)

    #TSV
    participant_tsv = participants.loc[:, [u'participant_id', u'sex', u'age']]
    participant_tsv.loc[:, u'participant_id'] = u'sub-' + participant_tsv.loc[:, u'participant_id'].astype(unicode)
    participant_tsv.to_csv(BIDS + u'participants.tsv', sep=u'\t', index=False)


# In[15]:

def convert_to_bids(participants, protocol):
    
    print u"Comparing Folders to Protocol...\n"
    
    if check_against_protocol(participants,protocol): #Function returns true is everything matches
        
        print u"Creating BIDS_data folder\n"
        #Make BIDS Folder
        makefolder(BIDS)
        participants.participant_id.apply(lambda x: makefolder(BIDS + u'sub-' + unicode(x) + u"/anat"))
        participants.participant_id.apply(lambda x: makefolder(BIDS + u'sub-' + unicode(x) + u"/func"))
        
        for index, row in participants.iterrows():
            #Get files
            NIMS_participant_filenames = os.listdir(NIMS + row.nims_title)

            #Delete all non-nii.gz files from list
            NIMS_participant_filenames = [x for x in NIMS_participant_filenames if u".nii.gz"  in x]

            for item in set(NIMS_protocol_filenames):
                directory_filenames = [x for x in NIMS_participant_filenames if item in x]
                protocol_filenames = NIMS_BIDS_conversion[NIMS_BIDS_conversion.NIMS_scan_title.unicode.contains(item)]
                protocol_filenames = protocol_filenames.iloc[:,1].tolist()

                for index, item in enumerate(directory_filenames):
                    oldpath = (NIMS + row.nims_title + u"/" + directory_filenames[index])
                    newpath = (protocol_filenames[index].replace(u"###", unicode(row.participant_id)))
                    copyfile(oldpath, newpath)

                    print u"sub-" + unicode(row.participant_id) + u": ++ "+ os.path.basename(newpath).rjust(20)
            print u"------------"

        print u"\nCreating JSON and .tsv Files"
        
        write_text_files(participants, protocol)
       
        print u"\nDone!"


# In[16]:

convert_to_bids(participants, protocol)

