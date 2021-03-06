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
import numpy as np  # Module that simplifies computations on matrices
from pylsl import StreamInlet, resolve_byprop  # Module to receive EEG data
import serial
import time
from sklearn.pipeline import make_pipeline
from pyriemann.estimation import ERPCovariances
from pyriemann.classification import MDM
from sklearn.model_selection import cross_val_score, StratifiedShuffleSplit, train_test_split
from sklearn import svm
from sklearn.metrics import accuracy_score


sns.set_context('talk')
sns.set_style('white')


# Load data from sample data
def load_data(subject_nb, sfreq=256., session_nb=1,
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
        './data/',
        'subject_{}/session_{}.csv'.format(subject_nb, session_nb))
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
        stim_ind (int): index of the stim channel (marker)
        replace_ch_names (dict or None): dictionary containing a mapping to
            rename channels. Useful when an external electrode was used.
    Returns:
        (mne.io.array.array.RawArray): loaded EEG
    """
    n_channel = len(ch_ind)

    raw = []

    # read the file [channels(4), aux, marker]
    data = pd.read_csv(filepath, index_col=0)
    print(data.columns)
    # name of each channels [channels, stim]
    ch_names = list(data.columns)[0:n_channel] + ['Stim']
    print(ch_names)

    if replace_ch_names is not None:
        ch_names = [c if c not in replace_ch_names.keys()
                    else replace_ch_names[c] for c in ch_names]

    # type of each channels
    ch_types = ['eeg'] * n_channel + ['stim']

    # get data and exclude Aux channel [{num of data}, 5]
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


# Load data from streaming
def stream_data(eeg_data, ch_names, ch_ind,):

    sfreq = 256

    n_channel = len(ch_ind)
    raw = []
    ch_types = ['eeg'] * n_channel + ['stim']
    ch_names = ch_names[0:n_channel] + ['stim']

    # create MNE object
    info = create_info(ch_names=ch_names, ch_types=ch_types,
                       sfreq=sfreq)

    # OddBall high prob(Non-target) -> Event id: 1. low prob(Target) -> Event id:2.
    testMarker = np.ones(eeg_data.shape[0], dtype=int)  # stim = marker
    testMarker[20] = 2
    testMarker[50] = 2
    testMarker[100] = 1
    testMarker[200] = 1

    # [{num of data},[index_channel + marker]]
    data = np.column_stack([eeg_data, testMarker])
    data = data.T
    data[:-1] *= 1e-6
    print(data.shape)
    raw.append(RawArray(data=data, info=info))
    return concatenate_raws(raw)


def plot_conditions(epochs, conditions=OrderedDict(), ci=97.5, n_boot=1000,
                    title='', palette=None, ylim=(-11, 12),
                    diff_waveform=(1, 2)):
    """Plot ERP conditions.
    Args:
        epochs (mne.epochs): EEG epochs
    Keyword Args:
        conditions (OrderedDict): dictionary that contains the names of the
            conditions to plot as keys, and the list of corresponding marker
            numbers as value. E.g.,
                conditions = {'Non-target': [0, 1],
                               'Target': [2, 3, 4]}
        ci (float): confidence interval in range [0, 100]
        n_boot (int): number of bootstrap samples
        title (str): title of the figure
        palette (list): color palette to use for conditions
        ylim (tuple): (ymin, ymax)
        diff_waveform (tuple or None): tuple of ints indicating which
            conditions to subtract for producing the difference waveform.
            If None, do not plot a difference waveform
    Returns:
        (matplotlib.figure.Figure): figure object
        (list of matplotlib.axes._subplots.AxesSubplot): list of axes
    """
    if isinstance(conditions, dict):
        conditions = OrderedDict(conditions)

    if palette is None:
        palette = sns.color_palette("hls", len(conditions) + 1)

    X = epochs.get_data() * 1e6
    times = epochs.times
    y = pd.Series(epochs.events[:, -1])

    fig, axes = plt.subplots(2, 2, figsize=[12, 6],
                             sharex=True, sharey=True)
    axes = [axes[1, 0], axes[0, 0], axes[0, 1], axes[1, 1]]

    # Plot data around epochs for each channel, segmented by Non-target or Target.
    for ch in range(4):
        for cond, color in zip(conditions.values(), palette):
            # Multiple epochs are covered in the following figure by bootstrap confidence interval.
            sns.tsplot(data=X[y.isin(cond), ch], time=times, color=color,
                       n_boot=n_boot, ci=ci, ax=axes[ch])

        if diff_waveform:
            diff = (np.nanmean(X[y == diff_waveform[1], ch], axis=0) -
                    np.nanmean(X[y == diff_waveform[0], ch], axis=0))
            # Difference between Targets and Non-Targets.
            axes[ch].plot(times, diff, color='k', lw=1)

        axes[ch].set_title(epochs.ch_names[ch])
        axes[ch].set_ylim(ylim)
        axes[ch].axvline(x=0, ymin=ylim[0], ymax=ylim[1], color='k',
                         lw=1, label='_nolegend_')

    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('Amplitude (uV)')
    axes[-1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Amplitude (uV)')

    if diff_waveform:
        legend = (['{} - {}'.format(diff_waveform[1], diff_waveform[0])] +
                  list(conditions.keys()))
    else:
        legend = conditions.keys()

    axes[-1].legend(legend)
    sns.despine()
    plt.tight_layout()
    plt.show()

    if title:
        fig.suptitle(title, fontsize=20)

    return fig, axes


def connect_to_eeg_stream():
    # 0 = left ear(TP9), 1 = left forehead(AF7), 2 = right forehead(AF8), 3 = right ear(TP10)
    index_channel = [0, 1, 2, 3]

    # Search for active LSL stream
    print('Looking for an EEG stream...')
    streams = resolve_byprop('type', 'EEG', timeout=2)
    if len(streams) == 0:
        raise RuntimeError('Can\'t find EEG stream.')

    # Set active EEG stream to inlet and apply time correction
    print("Start acquiring data")
    inlet = StreamInlet(streams[0], max_chunklen=12)
    eeg_time_correction = inlet.time_correction()

    # Get the stream info, description, sampling frequency, number of channels
    info = inlet.info()
    description = info.desc()
    fs = int(info.nominal_srate())
    n_channels = info.channel_count()

    # Get names of all channels
    ch = description.child('channels').first_child()
    ch_names = [ch.child_value('label')]
    for i in range(1, n_channels):
        ch = ch.next_sibling()
        ch_names.append(ch.child_value('label'))

    print('Start collecting for 20 seconds')
    eeg_data, timestamps = inlet.pull_chunk(
        timeout=20+1, max_samples=fs * 20)
    # [[{TP9}, {AF7}, {AF8}, {TP10}]]
    eeg_data = np.array(eeg_data)[:, index_channel]
    print('Finish collecting')
    raw_data = stream_data(eeg_data,
                           ch_names=ch_names, ch_ind=index_channel)

    return raw_data

 # See: https://mne.tools/stable/auto_tutorials/evoked/30_eeg_erp.html?highlight=amplitude#amplitude-and-latency-measures


def calculate_amp_and_lat_at_peak(epochs):
    good_tmin, good_tmax = .3, .4
    ch, lat, amp = epochs.average().get_peak(
        ch_type='eeg', tmin=good_tmin, tmax=good_tmax, mode='pos', return_amplitude=True)
    print(f'Peak Amplitude: {amp } uV')
    print(f'Latency: {lat } ms')
    return amp, lat


def train_svm_p300(epochs):
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
    return accuracy_score
