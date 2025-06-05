#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 25 12:31:10 2025
@author: Leela Srinivasan

Dependencies: AFNI
"""


import os
import sys
import shutil
import subprocess
import pandas as pd


def main(): 
    
    
    #Set data/paths
    subj=sys.argv[1]
    ses, subj_fs_dir=get_freesurfer_path(subj)
    d_data, d_model=set_project_folders(subj, ses)
    

    #Look for resection mask & align to native FS space
    find_resection(subj, d_model)
    align_resection_to_fs(subj, ses, d_model, subj_fs_dir)
    
    
    #Extract resected electrode coordinates, plot and merge to resection mask for viewing
    f_coords=prep_coords(d_data,d_model)
    plot_elec(d_model, f_coords)
    merge_surgical_estimates(d_model)
    
    
def plot_elec(d_model, coords):
    """
    

    Parameters
    ----------
    master : str
        filepath for base/master dataset (SurfVol).
    coords : str
        filepath for txtfile with coordinates formatted by write_coordfile.

    Returns
    -------
    None. Creates file resected_elec.nii

    """
    
    master=os.path.join(d_model, "mr_pre.nii")
    
    
    #Create nifti from coordinate file
    pref1=os.path.join(d_model, "resected_elec.nii")
    cmd1="3dUndump -prefix {} -master {} -dval 1 -srad 2 -xyz {}"
    cmd1=cmd1.format(pref1, master, coords)
    subprocess.run(cmd1,shell=True)
    
    

    #Perform LR flip
    pref2=os.path.join(d_model, "resected_elec.nii")
    cmd2="3dLRflip -prefix {} {}"
    cmd2=cmd2.format(pref2, pref1)
    subprocess.run(cmd2,shell=True)
    os.remove(pref1)


def merge_surgical_estimates(d_model):
    """
    

    Parameters
    ----------
    d : str
        path to parent directory.

    Returns
    -------
    None. Created merged nifti with resection mask and electrode estimates.

    """
    

    if 'rsxn_al.nii' and 'resected_elec.nii' in os.listdir(d_model):
        fa=os.path.join(d_model, 'rsxn_al.nii')
        fb=os.path.join(d_model, 'resected_elec.nii')
        pref=os.path.join(d_model, 'combined_estimates.nii')
        
        
        #Use 3dcalc to combine niftis, setting resected electrodes with val=2
        cmd1="3dcalc -a {} -b {} -expr 'step(a)+(step(b)*2)' -prefix {}"
        cmd1=cmd1.format(fa, fb, pref)
        subprocess.run(cmd1,shell=True)
        print("Launch AFNI from {} to view outputs. Script complete.".format(d_model))
        

def write_coordfile(df, outname):
    """

    Parameters
    ----------
    df : df
        df of isolated coordinates to write to txtfile as per 3dUndump
    outname : str
        path of desired output file.

    Returns
    -------
    None. Writes coordinates to outname in the format required by 3dUndump arg "-xyz"

    """
    lines=[]
    for ind, row in df.iterrows():
        line=' '.join([str(i) for i in [row.x, row.y, row.z]])
        lines.append(line)
    
    with open(outname, "w",encoding="utf-8") as fo:
        fo.write('\n'.join(lines))

        
def get_freesurfer_path(subj):
    """

    Parameters
    ----------
    subj : str
        p***.

    Raises
    ------
    Exception
        If unable to find FS paths.

    Returns
    -------
    ses : str
        clinical/altclinical.
    subj_fs_dir : str
        path to subject FS dir.

    """
    
    
    fs_dir='/Volumes/Shares/NEU/Data/derivatives/freesurfer-6.0.0/'
    bids_prefix="sub-{}_ses-".format(subj)
    
    
    #Search for FS dir as per the recon-all processing stream
    if os.path.exists(os.path.join(fs_dir, bids_prefix+"clinical")):
        ses="clinical"
        subj_fs_dir=os.path.join(fs_dir, bids_prefix+"clinical")
    elif os.path.exists(os.path.join(fs_dir, bids_prefix+"altclinical")):
        ses="altclinical"
        subj_fs_dir=os.path.join(fs_dir, bids_prefix+"altclinical")
    else:
        raise Exception("FreeSurfer has not been run for {}. Exiting...".format(subj))
    return ses, subj_fs_dir
    

def set_project_folders(subj, ses):
    """

    Parameters
    ----------
    subj : str
        p***.

    Raises
    ------
    Exception
        If required data (leads.csv and element_info.csv missing.

    Returns
    -------
    d_data : str
        path to data dir.
    d_model : str
        path to working/model dir.

    """
    
    d_base=os.path.join("/Volumes/Shares/NEU/Projects/MEG_iEEG", subj)
    if not os.path.exists(d_base):
        raise Exception("Subject MEG_iEEG folder does not exist. Exiting...")
        
        
    d_data=os.path.join(d_base, "data")
    if 'leads.csv' and 'element_info.csv' not in os.listdir(d_data):
        raise Exception("Subject missing resected electrode csv data. Exiting...")
        
        
    d_model=os.path.join(d_base, "model")
    if not os.path.exists(d_model):
        os.makedirs(d_model)
        
        
    import_t1(subj, ses, d_model)
    return d_data, d_model
    

def convert_grids(df):
    """

    Parameters
    ----------
    df : df
        input df, like element_info.csv.

    Returns
    -------
    elec_list : list
        list of electrodes that correspond to leads.csv.

    """
    elec_list=[]
    for ind, row in df.iterrows():
        locs=row.isResected[1:-1].split(" ")
        for loc in locs:
            elec_list.append(row.tagName + loc)
    return elec_list
        

def prep_coords(d_data, d_model):
    """

    Parameters
    ----------
    d : str
        path to working directory that contains resection files (leads.csv and element_info.csv).

    Returns
    -------
    f_coords : str
        path to written coordfile for use by 3dUndump.

    """
    
    #Read CSV data and limit to resected elements
    leads_df=pd.read_csv(d_data + "/leads.csv")
    info_df=pd.read_csv(d_data + "/element_info.csv")
    subset_info_df=info_df[info_df.isResected != '[]']
    
    
    #Extract overlapping information and write to coordinate file for AFNI 3dUndump
    elec_list=convert_grids(subset_info_df)
    resected_coords=leads_df[leads_df.chanName.isin(elec_list)].reset_index(drop=True)
    f_coords=os.path.join(d_model, "resected_coords.txt")
    write_coordfile(resected_coords, f_coords)
    return f_coords
    
    
def import_surfvol(subj, session, d_model, subj_fs_dir):
    """

    Parameters
    ----------
    subj : str
        p***.
    session : str
        clinical/altclinical.
    d : str
        path to working directory.
    subj_fs_dir : str
        path to freesurfer derivatives subj dir.

    Returns
    -------
    None. Brings SurfVol into d.

    """
    
    if 'sub-{}_{}_SurfVol.nii'.format(subj,session) in os.listdir(d_model):
        return
    shutil.copyfile(os.path.join(subj_fs_dir, 'SUMA', 'sub-{}_ses-{}_SurfVol.nii'.format(subj,session)),os.path.join(d_model,'sub-{}_ses-{}_SurfVol.nii'.format(subj,session)))
    
    
    
def import_t1(subj, session, d_model):
    
    bids_base='/Volumes/Shares/NEU/Data/'
    bids_subj_folder=os.path.join(bids_base, 'sub-{}'.format(subj), 'ses-{}'.format(session), 'anat')
    f=os.path.join(bids_subj_folder, 'sub-{}_ses-{}_rec-axialized_T1w.nii.gz'.format(subj, session))
    if os.path.exists(f):
        shutil.copyfile(f, os.path.join(d_model, 't1.nii.gz'))
    
    
def find_resection(subj, d_model):
    """


    Parameters
    ----------
    subj : str
        p***.
    d : str
        path to working directory.

    Returns
    -------
    None. Moves resection .msk.nii and t1 files into working directory

    """
    
    #Set dir options
    prefix='/Volumes/Shares/NEU/Projects/resection_mask'
    default_dir=os.path.join(prefix, subj, 'rsxn_msk')
    alt_dir=os.path.join(prefix,'__alternateMRIs',subj,'rsxn_msk')
    
    
    #Search for .msk.nii file and resection t1w image
    for dir_option in [default_dir, alt_dir]:
        if 'rsxn.msk.nii' in os.listdir(dir_option):
            shutil.copyfile((os.path.join(dir_option,'rsxn.msk.nii')),(os.path.join(d_model,'rsxn.msk.nii')))
            for f in os.listdir(os.path.join(dir_option,'prep')):
                if f in ['t1.nii', 'preop_t1.nii']:
                    shutil.copyfile((os.path.join(dir_option, 'prep', f)),os.path.join(d_model,'resection_t1.nii'))
            return
                    
    
def align_resection_to_fs(subj, session, d_model, subj_fs_dir):
    """
    

    Parameters
    ----------
    subj : str
        p***.
    session : str
        clinical/altclinical.
    d : str
        path to working directory.

    Returns
    -------
    None. Aligns resection mask and outputs rsxn_al.nii

    """
    
    if 'rsxn_al.nii' in os.listdir(d_model):
        return 
    if 'rsxn.msk.nii' and 'resection_t1.nii' in os.listdir(d_model):
        os.chdir(d_model)
        import_surfvol(subj, session, d_model, subj_fs_dir)
        
        
        #Create transformation matrix
        cmd1="3dAllineate -base sub-{}_ses-{}_SurfVol.nii -source resection_t1.nii -prefix aligned+orig -1Dmatrix_save anat_to_fs"
        cmd1=cmd1.format(subj,session)
        subprocess.run(cmd1,shell=True)
        
        
        #Apply transformation matrix
        cmd2="3dAllineate -base sub-{}_ses-{}_SurfVol.nii -source rsxn.msk.nii -1Dmatrix_apply anat_to_fs.aff12.1D -prefix tmp_rsxn+orig"
        cmd2=cmd2.format(subj,session)
        subprocess.run(cmd2,shell=True)
        
        
        #Ensure you are extracting positive mask pieces
        sub_cmd="3dcalc -a tmp_rsxn+orig -expr 'ispositive(a-0.1)' -prefix tmp2_rsxn.nii"
        subprocess.run(sub_cmd,shell=True)
        
        
        #Fill mask holes
        msk_cmd="3dmask_tool -input tmp2_rsxn.nii -prefix rsxn_al.nii -fill_holes"
        subprocess.run(msk_cmd,shell=True)
        
        
        #Remove all temp files
        for file in os.listdir(os.getcwd()):
            for tmp_file in ['aligned+orig', 'anat_to_fs', 'tmp_rsxn+orig', 'tmp2_rsxn', 'rsxn.msk.nii', 'resection_t1.nii']:
                if tmp_file in file:
                    os.remove(file)

    

if __name__ == "__main__":
    main()
