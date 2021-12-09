# Get data with Muse lsl and marker induced by visual stimuli
# See: https://neurotechx.github.io/eeg-notebooks/auto_examples/visual_p300/00x__p300_run_experiment.html?highlight=muse

from EEG import EEG
import oddball_task_gui
import pathlib


# Define some variables
board_name = "muse2"
experiment = "visual_p300"
subject_id = 1
session_nb = "1_normal"  # {}_normal: red/blue, {}_emotion: scared/peace,
record_duration = 100

eeg_device = EEG(device=board_name)

# Create save file name
filePath = "./data/subject_{}/session_{}.csv"
save_fn = pathlib.Path(filePath.format(subject_id, session_nb))

oddball_task_gui.present(duration=record_duration,
                         eeg=eeg_device, save_fn=save_fn)
