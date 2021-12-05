# P300-muse
Get P300 data using Muse

## Run
1. Start Oddball task

  `python visual-p300.py`

2. Modify created CSV

As a known bug, the created CSV file doesn't have column name `Marker` somehow. So, add the `Marker` column name to the CSV file, and remove a few sentences that don't include markers.

3. Process your realtime data

  `python P300-training.py`
