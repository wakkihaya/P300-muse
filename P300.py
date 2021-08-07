import sys
from collections import OrderedDict

from mne import create_info, concatenate_raws, Epochs, find_events
from mne.io import RawArray
from mne.channels import read_custom_montage

import pandas as pd
import numpy as np

from glob import glob
import seaborn as sns
from matplotlib import pyplot as plt
import utils

if __name__ == "__main__":
    subject = 1
    # Read raw data from muse device
    raw = utils.load_data('p300', sfreq=256.,
                          subject_nb=subject,
                          ch_ind=[0, 1, 2, 3])

    # raw.plot_psd(tmax=np.inf)

    raw.filter(1, 30, method='iir')    # Filter by 30 Hz

    events = find_events(raw)
    event_id = {'Non-Target': 1, 'Target': 2}

    epochs = Epochs(raw, events=events, event_id=event_id, tmin=-0.1, tmax=0.8, baseline=None,
                    reject={'eeg': 100e-6}, preload=True, verbose=False, picks=[0, 1, 2, 3])

    # Epoch average
    conditions = OrderedDict()
    conditions['Non-target'] = [1]
    conditions['Target'] = [2]

    # //TODO: not showing plot
    fig, ax = utils.plot_conditions(epochs, conditions=conditions,
                                    ci=97.5, n_boot=1000, title='',
                                    diff_waveform=(1, 2))
