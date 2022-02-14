import sys
from collections import OrderedDict

from mne import Epochs, find_events

import pandas as pd
import numpy as np

import seaborn as sns
from matplotlib import pyplot as plt
import utils

if __name__ == "__main__":
    subject = 1
    session = "10_emotion"  # {}_normal: red/blue, {}_emotion: scared/peace,
    # Read raw data from data set
    raw = utils.load_data(sfreq=256.,
                          subject_nb=subject, session_nb=session,
                          ch_ind=[0, 1, 2, 3])

    # Read raw data from muse device
    # raw = utils.connect_to_eeg_stream()

   #  raw.plot_psd(tmax=np.inf)  # X: Frequency, Y: デシベル(dB)

    raw.filter(1, 30, method='iir')    # Filter by 30 Hz

    events = find_events(raw)
    # Events include the labels -> 1: Not-P300, 2: P300.
    event_id = {'Non-Target': 1, 'Target': 2}

    # print(events)

    epochs = Epochs(raw, events=events, event_id=event_id, tmin=-0.1,
                    tmax=0.8, baseline=None,
                    reject=None,
                    preload=True, verbose=False, picks=[0, 1, 2, 3])
    if epochs.events.size == 0:
        print('No epochs')
    else:
        # See: https://mne.tools/stable/generated/mne.Epochs.html?highlight=apply_hilbert#mne.Epochs.apply_hilbert
        epochs.apply_hilbert()
        # Show Epocs plot with events.
        epochs.plot(events=events)

       # Calculate Amplitude and Latency on the peak.
        amp, lat = utils.calculate_amp_and_lat_at_peak(epochs)

        # Epoch average
        conditions = OrderedDict()
        conditions['Non-target'] = [1]
        conditions['Target'] = [2]

        fig, ax = utils.plot_conditions(epochs, conditions=conditions,
                                        ci=97.5, n_boot=1000, title='',
                                        diff_waveform=(1, 2))

        # Train P300 classifier.
        accuracy_score = utils.train_svm_p300(epochs)
