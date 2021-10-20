# See: https://github.com/NeuroTechX/eeg-notebooks/blob/beaa8a5c5e6c4e1e012afa23687ea328e5b46bb0/eegnb/experiments/visual_p300/p300.py
import os
from time import time
from glob import glob
from random import choice

import numpy as np
from pandas import DataFrame
from psychopy import visual, core, event

from eegnb import generate_save_fn
from eegnb.stimuli import CAT_DOG

__title__ = "Visual P300"


def present(duration, eeg=None, save_fn=None):
    n_trials = 2010
    iti = 0.4
    soa = 0.3
    jitter = 0.2
    record_duration = np.float32(duration)
    markernames = [1, 2]
    target_img_percent = 0.1

    non_target_marker_list = np.zeros(
        int(n_trials * (1.0 - target_img_percent)))
    target_marker_list = np.ones(int(n_trials * target_img_percent))
    image_type_list = np.concatenate(
        [non_target_marker_list, target_marker_list])
    np.random.shuffle(image_type_list)

    # Setup trial list
    trials = DataFrame(
        dict(image_type=image_type_list, timestamp=np.zeros(n_trials)))

    def load_image(imagePath):
        return visual.ImageStim(win=mywin, image=imagePath)

    # Setup graphics
    mywin = visual.Window(
        [600, 400], monitor="testMonitor", units="deg", fullscr=False)

    target = load_image(
        os.path.join(".", "stimulus/red.png"))
    nontarget = load_image(
        os.path.join(".", "stimulus/blue.png"))

    # Show instructions
    show_instructions(duration=duration)
    # start the EEG stream, will delay 5 seconds to let signal settle
    if eeg:
        if save_fn is None:  # If no save_fn passed, generate a new unnamed save file
            save_fn = generate_save_fn(
                eeg.device_name, "visual_p300", "unnamed")
            print(
                f"No path for a save file was passed to the experiment. Saving data to {save_fn}"
            )
        eeg.start(save_fn, duration=record_duration)

    # Iterate through the events
    start = time()

    for ii, trial in trials.iterrows():
        # Inter trial interval
        core.wait(iti + np.random.rand() * jitter)

        # Select and display image
        label = int(trials["image_type"].iloc[ii])
        if label == 1:
            target.draw()
        else:
            nontarget.draw()

        # Push sample
        if eeg:
            timestamp = time()
            marker = [markernames[label]]
            eeg.push_sample(marker=marker, timestamp=timestamp)

        mywin.flip()

        # offset
        core.wait(soa)
        mywin.flip()
        if len(event.getKeys()) > 0 or (time() - start) > record_duration:
            break

        event.clearEvents()

    # Cleanup
    if eeg:
        eeg.stop()
    mywin.close()


def show_instructions(duration):

    instruction_text = """
    Welcome to the P300 experiment!

    Stay still, focus on the centre of the screen, and try not to blink.
    Try to count the red image.

    This block will run for %s seconds.
    Press spacebar to continue.

    """
    instruction_text = instruction_text % duration

    # graphics
    mywin = visual.Window(
        [1300, 600], monitor="testMonitor", units="deg", fullscr=False)

    mywin.mouseVisible = False

    # Instructions
    text = visual.TextStim(
        win=mywin, text=instruction_text, color=[-1, -1, -1])
    text.draw()
    mywin.flip()
    event.waitKeys(keyList="space")

    mywin.mouseVisible = True
    mywin.close()
