from glob import glob
import os
from collections import OrderedDict

from mne import create_info, concatenate_raws
from mne.io import RawArray
from mne.channels import make_standard_montage
import pandas as pd
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt


def load_data(data_dir, subject_nb=1, sfreq=256.,
              ch_ind=[0, 1, 2, 3], stim_ind=5, replace_ch_names=None):
    """Load CSV files from the /data directory into a Raw object.
    Args:
        data_dir (str): directory inside /data that contains the
            CSV files to load, e.g., 'auditory/P300'
    Keyword Args:
        subject_nb (int or str): subject number. If 'all', load all
            subjects.
        session_nb (int or str): session number. If 'all', load all
            sessions.
        sfreq (float): EEG sampling frequency
        ch_ind (list): indices of the EEG channels to keep
        stim_ind (int): index of the stim channel
        replace_ch_names (dict or None): dictionary containing a mapping to
            rename channels. Useful when an external electrode was used.
    Returns:
        (mne.io.array.array.RawArray): loaded EEG
    """
    if subject_nb == 'all':
        subject_nb = '*'

    data_path = os.path.join(
        './data/', data_dir,
        'subject{}.csv'.format(subject_nb))
    return load_muse_csv_as_raw(data_path, sfreq=sfreq, ch_ind=ch_ind,
                                stim_ind=stim_ind,
                                replace_ch_names=replace_ch_names)


def load_muse_csv_as_raw(filepath, sfreq=256., ch_ind=[0, 1, 2, 3],
                         stim_ind=5, replace_ch_names=None):
    """Load CSV files into a Raw object.
    Args:
        filename (str or list): path or paths to CSV files to load
    Keyword Args:
        subject_nb (int or str): subject number. If 'all', load all
            subjects.
        session_nb (int or str): session number. If 'all', load all
            sessions.
        sfreq (float): EEG sampling frequency
        ch_ind (list): indices of the EEG channels to keep
        stim_ind (int): index of the stim channel
        replace_ch_names (dict or None): dictionary containing a mapping to
            rename channels. Useful when an external electrode was used.
    Returns:
        (mne.io.array.array.RawArray): loaded EEG
    """
    n_channel = len(ch_ind)

    raw = []

    # read the file
    data = pd.read_csv(filepath, index_col=0)

    # name of each channels
    ch_names = list(data.columns)[0:n_channel] + ['Stim']

    if replace_ch_names is not None:
        ch_names = [c if c not in replace_ch_names.keys()
                    else replace_ch_names[c] for c in ch_names]

    # type of each channels
    ch_types = ['eeg'] * n_channel + ['stim']
    montage = make_standard_montage('standard_1005')

    # get data and exclude Aux channel
    data = data.values[:, ch_ind + [stim_ind]].T

    # convert in Volts (from uVolts)
    data[:-1] *= 1e-6

    # create MNE object
    info = create_info(ch_names=ch_names, ch_types=ch_types,
                       sfreq=sfreq)
    raw.append(RawArray(data=data, info=info))

    # concatenate all raw objects
    raws = concatenate_raws(raw)

    return raws
