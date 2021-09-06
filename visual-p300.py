# Get data with Muse lsl and marker induced by visual stimuli
# See: https://neurotechx.github.io/eeg-notebooks/auto_examples/visual_p300/00x__p300_run_experiment.html?highlight=muse

from eegnb import generate_save_fn
from eegnb.devices.eeg import EEG
import oddball_task_gui

# Define some variables
board_name = "muse"
experiment = "visual_p300"
subject_id = 0
session_nb = 0
record_duration = 120

eeg_device = EEG(device=board_name)

# Create save file name
save_fn = generate_save_fn(board_name, experiment, subject_id, session_nb)
print(save_fn)

oddball_task_gui.present(duration=record_duration,
                        eeg=eeg_device, save_fn=save_fn)

#TODO: Confirm
#1. Save data with 5 channels data and markers. like subject1.csv
#2. Output information by `python P300.py`
