""" Abstraction for the various supported EEG devices.

    1. Determine which backend to use for the board.
    2.

"""

import sys
import time
import logging
from time import sleep
from multiprocessing import Process

import numpy as np
import pandas as pd

from brainflow import BoardShim, BoardIds, BrainFlowInputParams
from muselsl import stream, list_muses, record, constants as mlsl_cnsts
from pylsl import StreamInfo, StreamOutlet, StreamInlet, resolve_byprop

from eegnb.devices.utils import get_openbci_usb, create_stim_array, SAMPLE_FREQS, EEG_INDICES, EEG_CHANNELS


logger = logging.getLogger(__name__)

# list of brainflow devices
brainflow_devices = [
    "ganglion",
    "ganglion_wifi",
    "cyton",
    "cyton_wifi",
    "cyton_daisy",
    "cyton_daisy_wifi",
    "brainbit",
    "unicorn",
    "synthetic",
    "brainbit",
    "notion1",
    "notion2",
    "freeeeg32",
    "crown",
]


class EEG:
    device_name: str
    stream_started: bool = False

    def __init__(
        self,
        device=None,
        serial_port=None,
        serial_num=None,
        mac_addr=None,
        other=None,
        ip_addr=None,
    ):
        """The initialization function takes the name of the EEG device and determines whether or not
        the device belongs to the Muse or Brainflow families and initializes the appropriate backend.

        Parameters:
            device (str): name of eeg device used for reading data.
        """
        # determine if board uses brainflow or muselsl backend
        self.device_name = device
        self.serial_num = serial_num
        self.serial_port = serial_port
        self.mac_address = mac_addr
        self.ip_addr = ip_addr
        self.other = other
        self.backend = self._get_backend(self.device_name)
        self.initialize_backend()
        self.n_channels = len(EEG_INDICES[self.device_name])
        self.sfreq = SAMPLE_FREQS[self.device_name]

    def initialize_backend(self):
        if self.backend == "brainflow":
            self._init_brainflow()
            self.timestamp_channel = BoardShim.get_timestamp_channel(
                self.brainflow_id)
        elif self.backend == "muselsl":
            self._init_muselsl()
            # self._muse_get_recent()  # run this at initialization to get some
            # stream metadata into the eeg class TODO:

    def _get_backend(self, device_name):
        if device_name in brainflow_devices:
            return "brainflow"
        elif device_name in ["muse2016", "muse2", "museS"]:
            return "muselsl"

    #####################
    #   MUSE functions  #
    #####################
    def _init_muselsl(self):
        # Currently there's nothing we need to do here. However keeping the
        # option open to add things with this init method.
        self._muse_recent_inlet = None

    def _start_muse(self, duration):
        # Look for muses
        self.muses = list_muses()
        # self.muse = muses[0]

        # Start streaming process
        self.stream_process = Process(
            target=stream, args=(self.muses[0]["address"],)
        )
        self.stream_process.start()

        # Create markers stream outlet
        self.muse_StreamInfo = StreamInfo(
            "Markers", "Markers", 1, 0, "int32", "myuidw43536"
        )
        self.muse_StreamOutlet = StreamOutlet(self.muse_StreamInfo)

        # Start a background process that will stream data from the first available Muse
        print("starting background recording process")
        if self.save_fn:
            print("will save to file: %s" % self.save_fn)
        self.recording = Process(target=record, args=(duration, self.save_fn))
        self.recording.start()

        time.sleep(5)
        self.stream_started = True
        self.push_sample([99], timestamp=time.time())

    def _stop_muse(self):
        pass

    def _muse_push_sample(self, marker, timestamp):
        self.muse_StreamOutlet.push_sample(marker, timestamp)

    def _muse_get_recent(self, n_samples: int = 256, restart_inlet: bool = False):
        if self._muse_recent_inlet and not restart_inlet:
            inlet = self._muse_recent_inlet
        else:
            # Initiate a new lsl stream
            streams = resolve_byprop(
                "type", "EEG", timeout=mlsl_cnsts.LSL_SCAN_TIMEOUT)
            if not streams:
                raise Exception(
                    "Couldn't find any stream, is your device connected?")
            inlet = StreamInlet(
                streams[0], max_chunklen=mlsl_cnsts.LSL_EEG_CHUNK)
            self._muse_recent_inlet = inlet

        info = inlet.info()
        sfreq = info.nominal_srate()
        description = info.desc()
        n_chans = info.channel_count()

        self.sfreq = sfreq
        self.info = info
        self.n_chans = n_chans

        timeout = (n_samples/sfreq)+0.5
        samples, timestamps = inlet.pull_chunk(timeout=timeout,
                                               max_samples=n_samples)

        samples = np.array(samples)
        timestamps = np.array(timestamps)

        ch = description.child("channels").first_child()
        ch_names = [ch.child_value("label")]
        for i in range(n_chans):
            ch = ch.next_sibling()
            lab = ch.child_value("label")
            if lab != "":
                ch_names.append(lab)

        df = pd.DataFrame(samples, index=timestamps, columns=ch_names)
        return df

    #################################
    #   Highlevel device functions  #
    #################################

    def start(self, fn, duration=None):
        """Starts the EEG device based on the defined backend.

        Parameters:
            fn (str): name of the file to save the sessions data to.
        """
        if fn:
            self.save_fn = fn

        if self.backend == "brainflow":
            self._start_brainflow()
            self.markers = []
        elif self.backend == "muselsl":
            self._start_muse(duration)

    def push_sample(self, marker, timestamp):
        """
        Universal method for pushing a marker and its timestamp to store alongside the EEG data.

        Parameters:
            marker (int): marker number for the stimuli being presented.
            timestamp (float): timestamp of stimulus onset from time.time() function.
        """
        if self.backend == "brainflow":
            self._brainflow_push_sample(marker=marker)
        elif self.backend == "muselsl":
            self._muse_push_sample(marker=marker, timestamp=timestamp)

    def stop(self):
        if self.backend == "brainflow":
            self._stop_brainflow()
        elif self.backend == "muselsl":
            pass

    def get_recent(self, n_samples: int = 256):
        """
        Usage:
        -------
        from eegnb.devices.eeg import EEG
        this_eeg = EEG(device='museS')
        df_rec = this_eeg.get_recent()
        """

        if self.backend == "brainflow":
            df = self._brainflow_get_recent(n_samples)
        elif self.backend == "muselsl":
            df = self._muse_get_recent(n_samples)
        else:
            raise ValueError(f"Unknown backend {self.backend}")
        return df
