import sys
from collections import OrderedDict

from mne import create_info, concatenate_raws
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
    raw = utils.load_data('p300', sfreq=256.,
                          subject_nb=subject,
                          ch_ind=[0, 1, 2, 3])
    print(raw)
