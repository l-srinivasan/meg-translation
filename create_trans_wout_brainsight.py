#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 2 10:32:58 2025
@authors: Leela Srinivasan, Elena Hayday

Create run-specific transformation + fiducial files in the abscence of Brainsight and the Exported_Electrodes.txt coordinates
Manually mark the fiducial locations on AFNI

"""


import os
import shlex
import subprocess
import sys
import shutil
from time import sleep


import warnings
warnings.filterwarnings(action='ignore', category=FutureWarning)


def create_null_tag_file():
    """
    
    Create an empty null.tag file which facilitates tagset labeling
    
    Returns
    -------
    None.

    """
    
    fids = ["'Nasion'", "'Left Ear'", "'Right Ear'"]
    with open("null.tag", "w") as f:
        for fid in fids:
            f.write(fid + " 0 0 0\n")
            
  
def convert_anat(fs_subj):
    """
    
    Convert anatomical t1w from nifti to HEAD/BRIK format

    Parameters
    ----------
    fs_subj : str
        FreeSurfer subject name.

    Returns
    -------
    None.

    """
    nii_mri_file = f'{fs_subj}_rec-axialized_T1w.nii.gz'
    mri_file_stem = 't1+orig'
    copy_cmd = shlex.split(f"3dcopy {nii_mri_file} {mri_file_stem}.")
    subprocess.run(copy_cmd)
    
    
def view_afni(
    message="Press return when finished", underlay=None, overlay=None, plugout=False
):

    plugout_str1, plugout_str2 = "", ""
    if plugout:
        plugout_str1 = " -yesplugouts"
        plugout_str2 = " -com 'OPEN_WINDOW A.plugin.Edit_Tagset'"
    underlay_str = ""
    if underlay:
        underlay_str = f" -com 'SWITCH_UNDERLAY {underlay}'"
    overlay_str = ""
    if overlay:
        overlay_str = f" -com 'SWITCH_OVERLAY {overlay}'"

    cmd = shlex.split(f"afni{plugout_str1}{underlay_str}{overlay_str}{plugout_str2}")
    print(cmd)
    subprocess.call(cmd)
    sleep(5)
    user_input = input(f"{message}")

    return user_input


def check_failure(
    err, errors=["N", "'N'", "n", "'n'"], message="++ Tagset marked as bad. Skipping ++"
):

    if err in errors:
        print(message)
        sys.exit(1)
        
        
def main():
    
    
    """
    MODIFY USER DEFINED BIDS ROOT
    """
    bids_root = 'insert_user_path'
    fs_dir = bids_root / 'derivatives' / 'freesurfer-6.0.0'
    
    
    #Subject specific paths
    subj=sys.argv[1]
    ses=sys.argv[2]
    fs_subj=f'sub-{subj}_ses-{ses}'
    subj_fs_dir = fs_dir / fs_subj
    subj_source_dir = bids_root / 'sourcedata' / f'sub-{subj}'
    subj_source_meg_dir = subj_source_dir / 'ses-meg' / 'meg'
    fs_t1_dir = subj_source_dir / f'ses-{ses}' / 'anat'
        
        
    #Check if MEG data has been moved into /sourcedata
    if not subj_source_meg_dir.exists():
        print(f"++ {subj} does not have MEG data stored in {subj_source_meg_dir}. ++")
        sys.exit(1)
    
    
    #Set defaults
    os.chdir(fs_t1_dir)
    default_trans_file=subj_fs_dir / 'bem' / f"{fs_subj}-trans.fif"
    default_fid_file=subj_fs_dir / 'bem' / f"{fs_subj}-fiducials.fif"
    
    
    #Select one ds folder to make the trans from — we don't have Brainsight coordinates so it doesn't matter which run
    ds_folders=os.listdir(subj_source_meg_dir)
    example_ds=os.path.join(subj_source_meg_dir, ds_folders[0])
    create_null_tag_file()
    
    
    #Comvert the anatomical to BRIK/HEAD format
    nii_mri_file = f'{fs_subj}_rec-axialized_T1w.nii.gz'
    mri_file_stem = 't1+orig'
    copy_cmd = shlex.split(f"3dcopy {nii_mri_file} {mri_file_stem}.")
    subprocess.run(copy_cmd)
    
    
    #Manually mark the fiducials on the clinical scan in AFNI's GUI
    err = view_afni(
        message=(f"Open {mri_file_stem}.BRIK Dataset, type "
                "null.tag in 'Tag File' and click 'Read', reposition labels,"
                "hit 'Set' in between each one. When you're done, hit 'Save',"
                "then close AFNI and hit return in terminal when finished. O"
                "therwise, type 'N' and press return."),
        underlay=f"{mri_file_stem}.BRIK",
        plugout=True,
    )
    check_failure(err)
    os.remove("null.tag")


    """
    After hitting 'Save' and then the return key, you should see the message: 
    Over-writing dataset /{subj_source_dir}/ses-{ses}/anat/t1+orig.HEAD
    """
    
    
    #Create trans
    trans_cmd = shlex.split(
        f"calc_mnetrans.py -subjects_dir {fs_dir} -subject {fs_subj} -dsname {example_ds} -afni_mri {mri_file_stem}.BRIK"
    )
    subprocess.run(trans_cmd)
    
    
    #Replicate trans/fid for each run
    for ds_folder in ds_folders:
        run = ds_folder.split('.ds')[0][-2:]
        trans_file = subj_fs_dir / 'bem' / f"{fs_subj}-trans_{run}.fif"
        fid_file = subj_fs_dir / 'bem' / f"{fs_subj}-fiducials_{run}.fif"
        if trans_file.exists():
            print(f"++ Trans file already exists for {subj} and run {run} ++")
            sys.exit(1)
            
        shutil.copyfile(default_trans_file, trans_file)
        shutil.copyfile(default_fid_file, fid_file)
            
        
    #Remove defaults
    os.remove(default_trans_file)
    os.remove(default_fid_file)
            
            
if __name__ == "__main__":
    main()
