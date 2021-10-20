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
from sklearn.pipeline import make_pipeline
from pyriemann.estimation import ERPCovariances
from pyriemann.classification import MDM
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit, train_test_split
from sklearn import svm
from sklearn.metrics import accuracy_score

if __name__ == "__main__":
    subject = 0
    session = 2
    # Read raw data from data set
    raw = utils.load_data(sfreq=256.,
                          subject_nb=subject, session_nb=session,
                          ch_ind=[0, 1, 2, 3])

    # Read raw data from muse device
    # raw = utils.connect_to_eeg_stream()

    raw.plot_psd(tmax=np.inf)  # X: Frequency, Y: デシベル(dB)

    raw.filter(1, 30, method='iir')    # Filter by 30 Hz

    events = find_events(raw)
    # Events include the labels -> 1: Not-P300, 2: P300.
    event_id = {'Non-Target': 1, 'Target': 2}

    print(events)

    epochs = Epochs(raw, events=events, event_id=event_id, tmin=-0.1, tmax=0.8, baseline=None,
                    reject={'eeg': 100e-6}, preload=False, verbose=False, picks=[0, 1, 2, 3])
    #TODO: epochs are bad -> No epochs. See: https://mne.discourse.group/t/epoch-classifies-all-epochs-as-bad/1535
    if epochs.events.size == 0:
        print('No epochs')
    else:
        # Epoch average
        conditions = OrderedDict()
        conditions['Non-target'] = [1]
        conditions['Target'] = [2]

        fig, ax = utils.plot_conditions(epochs, conditions=conditions,
                                        ci=97.5, n_boot=1000, title='',
                                        diff_waveform=(1, 2))

        # Cross-validation (Using ERPCovariances, MDM)
        clf = make_pipeline(ERPCovariances(), MDM())
        epochs.pick_types(eeg=True)
        X = epochs.get_data() * 1e6  # (194, 4, 232)
        X = X.reshape(X.shape[0], -1)  # Convert to 2D (194, ~)
        times = epochs.times
        y = epochs.events[:, -1]  # (194,)

        cv = StratifiedShuffleSplit(
            n_splits=10, test_size=0.25, random_state=42)

        # Cross validation
        res = cross_val_score(clf, X, y == 2,
                              scoring='roc_auc', cv=cv, n_jobs=-1)

        # Make SVM model for specifying if P300 or Non-P300
        X_train, X_test, y_train, y_test = train_test_split(X, y)
        clf = svm.SVC()
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        print(accuracy_score(y_test, y_pred))
