#! /usr/bin/env python3.4
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from matplotlib.widgets import Button
from matplotlib import animation, style
from dataController import *
from dragHandler import *
from messageController import displayDialogBox, displayErrorBox
from tkinter import filedialog
import sys
from nvFspd import NvidiaFanController, updatedCurve
from os import path
import csv

style.use(['fivethirtyeight']) # current plot theme

# with plt.style.context("fivethirtyeight"):
#     mpl.rcParams["axes.grid"] = True
#     mpl.rcParams["axes.linewidth"]  = 1.25

""" Global Variables """
fig = plt.figure(num="Nvidia Fan Controller", figsize=(12, 9)) # create a figure (one figure per window)
fig.subplots_adjust(left=0.11, bottom=0.15, right=0.94, top=0.89, wspace=0.2, hspace=0)
axes = fig.add_subplot(1,1,1) # add a subplot to the figure. axes is of type Axes which contains most of the figure elements
update_stats = True # sets flag for updating chart with GPU stats
ticks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
""" --------------- """

class Chart():
	def __init__(self, notebook):
		global current_temp
		global current_fan_speed
		global nvidiaController
		global fig
		global dataController
		global line

		initChartValues()
	
		self.fig = fig # add plt.figure instance
		self.axes = axes # add a subplot instance to the figure
		self.canvas = FigureCanvas(self.fig) # add fig instance to a figure canvas
		self.canvas.set_size_request(800, 600) # set default canvas height (req'd for displaying the chart)

		self.graphTab = Gtk.Box()
		self.graphTab.add(self.canvas) # add plt figure canvas to the newly created gtkBox
		notebook.append_page(self.graphTab, Gtk.Label('Graph')) # add the gtkBox to the notebook
		
		self.anim = animation.FuncAnimation(self.fig, updateLabelStats, interval=1000) # updates chart w/ GPU stats every 1000ms

		# chart min/max display values
		self.x_min = -5 # sets the x min value for the background grid  
		self.x_max = 105 # sets the x max value for the background grid 
		self.y_min = 0 # sets the y min value for the background grid  
		self.y_max = 105 # sets the y max value for the background grid 

		# axes configurations
		self.axes.axhline(y=10, xmin=0, xmax=1, linewidth=1, color='red') # shows red a line across (10, 0) to represent lowest value
		self.axes.grid(linestyle='-', linewidth='0.1', color='grey')
		self.axes.set_xlim(self.x_min, self.x_max)
		self.axes.set_xticks(ticks)
		self.axes.set_ylim(self.y_min, self.y_max)
		self.axes.set_yticks(ticks)
		self.axes.set_title("GPU Fan Controller", fontsize=16)
		self.axes.tick_params(colors='0.7', which='both', labelsize=12)
		for axis in ['bottom','left']:
  			self.axes.spines[axis].set_color('0.1')
		plt.setp(self.axes.spines.values(), linewidth=0.2)
		# self.fig.patch.set_facecolor('0.15') # sets background color

		# matplotlib stops working if two buttons aren't present
		# [left, bottom, width, height]
		self.fig.add_axes([0, -100, 0.01, 0.01])
		self.fig.add_axes([0, 100, 0.01, 0.01])

		# creates curve w/ options: color=blue, s=squares, picker=max distance for selection
		line, = axes.plot(x_values, y_values, linestyle='-',  marker='s', markersize=4.5, color='b', picker=5, linewidth=1.5)

		self.dragHandler = DragHandler(self) # handles the mouse clicks on the curve
		dataController = DataController(x_values, y_values) # handles updating curve data

		# starts updating the GPU fan speeds
		nvidiaController = NvidiaFanController(x_values, y_values)
		nvidiaController.start()

	def close(self=None, widget=None, *data):
		plt.close('all')
		nvidiaController.stop()

def applyData():
	xdata = line.get_xdata() # grabs current curve y data
	ydata = line.get_ydata() # grabs current curve y data
	is_valid_curve = dataController.setData(xdata, ydata) # checks if curve is exponentially growing (returns bool)

	if is_valid_curve:
		updateChart(xdata, ydata) # updates nvFspd.NvidiaFanController() with new curve data
		displayDialogBox('Successfully applied the current curve to the fan settings!')
	else:
		xdata, ydata = dataController.getData() # gets previous data
		xydata = [xdata, ydata] 
		line.set_data(xydata) # resets line to previous curve

def initChartValues():
	global x_values
	global y_values

	# default curve values
	x_values = [0, 	11, 23, 34, 45, 55, 65, 74, 81, 88, 94, 100]
	y_values = [10, 15, 21, 27, 34, 41, 50, 59, 68, 78, 88, 100]

	cfg_x = []
	cfg_y = []

	# loads configuration array [temp, fspd] from csv
	if path.exists("config.csv"):
		try:
			with open('config.csv', 'r') as csvfile:
				config = csv.reader(csvfile, delimiter=',')
				for row in config:
					cfg_x.append(int(row[0]))
					cfg_y.append(int(row[1]))

			# updates default curve values with config array
			x_values = cfg_x #temp
			y_values = cfg_y #speed
		except:
			displayErrorBox("Failed to load configuration file. Falling back to a default curve.")

def resetData():
	initChartValues() # reset to initial values
	xydata = [x_values, y_values]
	line.set_data(xydata) # update curve with values
	updateChart(x_values, y_values) # update chart to reflect values

def saveToFile():
	config = '' # initialize config variable
	xdata, ydata = dataController.getData() # get current curve points

	for index in range(0, len(xdata)): 
		config += str(xdata[index]) + "," + str(ydata[index]) + "\n" # combines x and y curve data: (x, y) (x, y) ...etc as a string (req'd for writing out)

	#default saved as *.csv
	f = filedialog.asksaveasfile(mode='w', defaultextension=".csv") 

	if f is None: return # if dialog is canceled

	f.write(str(config)) # write string to file
	f.close() # close instance
	displayDialogBox('Successfully saved the current curve configuration!')

def setUpdateStats(bool):
	global update_stats
	update_stats = bool # whether or not update GPU stats


"""
Due to how the NvidiaFanController run loop was previously structured (to constantly update), there was an issue where updating the curve points could take anywhere from 3 to 10+ loop iterations
By pausing the loop, updates to the curve points occur consistently between 1-3 loop iterations
As a precaution, updating the chart with GPU temp/fan speed stats have also been paused, although may not be necessary.
"""
def updateChart(xdata, ydata):
	setUpdateStats(False) # temporarily stops live GPU updates
	updatedCurve(True) # pauses the nvFspd run loop
	nvidiaController.setCurve(xdata, ydata) # updates curve with new x and y data
	updatedCurve(False) # resumes nvFspd loop
	setUpdateStats(True) # enables live GPU updates

def updateLabelStats(i):
	if (update_stats):
		current_temp = NvidiaFanController().checkGPUTemp() # grabs current temp from NvidiaFanController
		axes.set_xlabel("Temperature "+ "(" + str(current_temp) + u"°C)", fontsize=12, labelpad=20) # updates chart x-axis label
		current_fan_speed = str(NvidiaFanController().checkFanSpeed()) # grabs current fspd from NvidiaFanController
		axes.set_ylabel("Fan Speed " + "(" + str(current_fan_speed) + u"%)", fontsize=12, labelpad=10) # updates chart y-axis label


if __name__ == '__main__':
	print ('Use GUI instead')