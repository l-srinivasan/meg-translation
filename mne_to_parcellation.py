#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 5 11:37:56 2025
@author: Leela Srinivasan

Map MNE virtual sensors in source estimate stc obj to parcellation type (eg. 'Schaefer2018_400Parcels_7Networks_order')
"""

import os
import sys
import mne
import numpy as np

def main():
    
    pnum_subj=sys.argv[1]
    dspm_run_dir=sys.argv[2]
    mri_subj_dir=sys.argv[3]
    parcellation_type=sys.argv[4]
    
    for hemi in ['lh', 'rh']:
        create_parcel_vertex_map(pnum_subj, dspm_run_dir, mri_subj_dir, parcellation_type)

def create_parcel_vertex_map():

    fname = os.path.join(dspm_run_dir, 'full-stcs-{}.stc'.format(hemi))
    stc=mne.read_source_estimate(fname)
    
    #Read cortical parcellation labels from a FreeSurfer annotation file, morph labels
    read_labels = mne.read_labels_from_annot('fsaverage', parc = parcellation_type, subjects_dir=mri_subj_dir)
    subject_labels = mne.morph_labels(read_labels, subject_to = pnum_subj, subjects_dir = mri_subj_dir)

    # Iterate over each parcel in subject_labels, finding vertices corresponding to the label vertices
    parcel_vertex_mapping = {}
    for parcel_num, label in enumerate(subject_labels):
        idx = np.nonzero(np.isin(stc.vertices[0 if hemi == 'lh' else 1], label.vertices))[0] 
        parcel_vertex_mapping[parcel_num] = [sensor + 2562 if hemi == 'rh' else sensor for sensor in idx]
        
    # Save hemispheric dictionary mapping to dSPM folder
    np.save(os.path.join(dspm_run_dir, "{}_parcel_vertex_mapping.npy".format(hemi)), parcel_vertex_mapping)


if __name__ == "__main__":
    main()
