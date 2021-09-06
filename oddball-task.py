# # -*- coding: utf-8 -*-

# # Target: [2], Non-target: [1], Nothing: [0]
# # See: https://github.com/yagijin/Oddball_P300
# # TODO: Send data of EEG from Muse at the same time.
# # -> need to set the same time duration between Muse and oddball task.

# import sys
# import random
# from time import perf_counter as pc, sleep
# from pylsl import StreamInfo, StreamOutlet, local_clock
# from muse import Muse
# from optparse import OptionParser

# from PyQt5.QtWidgets import QApplication,  QWidget
# from PyQt5.QtGui import QPainter,  QPixmap
# from PyQt5.QtCore import Qt, QTimer

# frameRate = 10  # timer's framerate
# printsec = 1  # Time for printing 1 stimulus
# sumOfStimulus = 10
# ratioOfTarget = 0.2
# targetPic = "stimulus/blue.png"  # Target
# nonTargetPic = "stimulus/red.png"  # Non-target


# class Stimulus:
#     def __init__(self, stimulusOrder):
#         self.on = 0
#         self.stimulusOrder = stimulusOrder
#         self.counterStimulus = 0
#         self.next_time = pc() + printsec
#         self.targetPic = QPixmap(targetPic)
#         self.nonTargetPic = QPixmap(nonTargetPic)

#     def resetTimer(self):
#         self.next_time = pc() + printsec

#     def draw(self, ctime):
#         painter = QPainter(window)

#         if (self.on == 1) or (self.on == 2):
#             if self.stimulusOrder[self.counterStimulus] == 0:

#                 painter.drawPixmap(75, 75, self.targetPic)

#             elif self.stimulusOrder[self.counterStimulus] == 1:
#                 painter.drawPixmap(75, 75, self.nonTargetPic)

#         if ctime >= self.next_time:
#             self.next_time += printsec
#             if (self.on == 1) or (self.on == 2):
#                 print(pc(), "s")
#                 self.counterStimulus = self.counterStimulus + 1
#                 self.on = 0
#                 print(self.counterStimulus, "stimulus")
#             else:
#                 if self.stimulusOrder[self.counterStimulus] == 0:
#                     self.on = 1
#                 elif self.stimulusOrder[self.counterStimulus] == 1:
#                     self.on = 2


# class MainWindow(QWidget):

#     def __init__(self):
#         super().__init__()
#         print("###  [Space] to Start and Pause/Unpause  ###")
#         self.base_time = pc()
#         self.OrderStimulus()
#         self.initStimulus()
#         self.initUI()
#         self.show()
#         self.connectToMuse()

#     def connectToMuse(self):
#         parser = OptionParser()
#         parser.add_option("-a", "--address",
#                           dest="address", type='string', default=None,
#                           help="device mac adress.")
#         parser.add_option("-n", "--name",
#                           dest="name", type='string', default=None,
#                           help="name of the device.")
#         parser.add_option("-b", "--backend",
#                           dest="backend", type='string', default="auto",
#                           help="pygatt backend to use. can be auto, gatt or bgapi")
#         parser.add_option("-i", "--interface",
#                           dest="interface", type='string', default=None,
#                           help="The interface to use, 'hci0' for gatt or a com port for bgapi")
#         (options, args) = parser.parse_args()

#         info = StreamInfo('Oddball-Muse', 'EEG', 6, 256,
#                           'float32', 'oddballstimulus-Muse')
#         info.desc().append_child_value("manufacturer", "Muse")
#         channels = info.desc().append_child("channels")

#         for c in ['TP9', 'AF7', 'AF8', 'TP10', 'Right AUX']:
#             channels.append_child("channel") \
#                 .append_child_value("label", c) \
#                 .append_child_value("unit", "microvolts") \
#                 .append_child_value("type", "EEG")
#         self.outlet = StreamOutlet(info, 12, 360)

#         def process(data, timestamps):
#             for ii in range(12):
#                 self.outlet.push_sample(data[:, ii], timestamps[ii])
#                 # TODO: wanna push_sample with stimuli

#         muse = Muse(address=options.address, callback=process,
#                     backend=options.backend, time_func=local_clock,
#                     interface=options.interface, name=options.name)

#         muse.connect()
#         print('Connected')
#         muse.start()
#         print('Streaming')

#         while 1:
#             try:
#                 sleep(1)
#             except:
#                 break

#         muse.stop()
#         muse.disconnect()
#         print('Disonnected')

#     def initUI(self):
#         self.setWindowTitle("Oddball-Task Stimulus")

#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.update)

#     def OrderStimulus(self):
#         self.stimulusOrder = list()

#         sumOfTarget = int(sumOfStimulus*ratioOfTarget)

#         for i in range(sumOfTarget):
#             self.stimulusOrder.append(0)
#         for i in range(sumOfStimulus-sumOfTarget):
#             self.stimulusOrder.append(1)

#         random.shuffle(self.stimulusOrder)

#     def initStimulus(self):
#         self.stim = Stimulus(self.stimulusOrder)

#     def keyPressEvent(self, e):
#         if e.key() == Qt.Key_Space:
#             if (self.stim.counterStimulus >= sumOfStimulus):
#                 self.timer.start()
#                 sys.exit()
#             elif self.timer.isActive():
#                 self.timer.stop()
#             else:
#                 self.stim.resetTimer()
#                 self.timer.start(frameRate)

#     def paintEvent(self, QPaintEvent):
#         curr_time = pc()
#         if (self.stim.counterStimulus >= sumOfStimulus):
#             print("###  [Space] to Exit from This App  ###")
#             self.timer.stop()
#         else:
#             self.stim.draw(curr_time)
#             stimu = [int(self.stim.on)]
#             self.outlet.push_sample(stimu)
#             print("Stim ", stimu)


# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.resize(700, 700)
#     sys.exit(app.exec_())
