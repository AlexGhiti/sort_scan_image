#!/usr/bin/env python

import os
import re
import subprocess
import time
import re
from threading import Thread
os.environ['KIVY_TEXT'] = 'pil'
from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
from kivy.app import App
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout 
from kivy.uix.boxlayout import BoxLayout 
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty


class PaperScanAndSort(EventDispatcher):
	# Path where frontend must copy final image for backend to sort it.
	#path_paper = "/nfs/home/aghiti/Projects/sort_scan_image/papers/unknown"
	path_paper = "/home/pi/sort_scan_image/papers/unknown"
	# Path where each individual page will be stored before being merged
	# into one paper copied in path_paper.
	path_page_paper = "/tmp/papers/"
	# ObjectProperty
	nb_page = NumericProperty(1)
	num_page = NumericProperty(0)	        # For display
	num_page_scanned = NumericProperty(0)   # For counting :)
	str_activity = StringProperty("No error")

	def __init__(self, *args, **kwargs):
		super(PaperScanAndSort, self).__init__(*args, **kwargs)
		self.th_scan = None
		self.bind(nb_page = kwargs["update_nb_page"])
		self.bind(num_page = kwargs["update_num_page"])
		self.bind(num_page_scanned = kwargs["update_num_page_scanned"])
		self.bind(str_activity = kwargs["update_activity"])

	# Attributes setters/getters
    # nb_page can be inc/dec while scanning paper,
    # but we need to take care that it is higher than
    # the number of scanned_page (TODO or discard all
    # the pages that are higher...).
	def nb_page_inc(instance, value):
		instance.nb_page += 1

	def nb_page_dec(instance, value):
	    if (instance.nb_page > 1 and instance.nb_page > instance.num_page_scanned):
			instance.nb_page -= 1

	def nb_page_clear(instance, value):
	    instance.nb_page = 1 

	def num_page_inc(instance, value):
		if (instance.num_page < instance.nb_page and instance.num_page < instance.num_page_scanned):
			instance.num_page += 1

	def num_page_dec(instance, value):
		if (instance.num_page >= 1):
			instance.num_page -= 1
                               
	def num_page_clear(instance, value):
		instance.num_page = 0

	def num_page_scanned_inc(instance, value):
		if (instance.num_page_scanned < instance.nb_page):
			instance.num_page_scanned += 1

	def num_page_scanned_dec(instance, value):
		if (instance.num_page_scanned >= 1):
			instance.num_page_scanned -= 1

	def num_page_scanned_clear(instance, value):
		instance.num_page_scanned = 0

 	def new_paper(instance, value):
        # TODO Stop thread that scans.
        #instance.th_scan.stop()
		# Clear attributes
		instance.num_page_clear(value)
		instance.num_page_scanned_clear(value)
		instance.nb_page_clear(value)
		# Clear path_page_paper
		cmd = "rm -rf %s" % os.path.join(instance.path_page_paper, "*")
		ret = subprocess.call(cmd.split(" "))
		if ret:
			instance.print_activity("[FAIL %d] %s" % (ret, cmd))

	def cancel_page(instance, value):
		instance.num_page_dec(value)
		instance.num_page_scanned_dec(value)
		cmd = "rm -rf %s" % os.path.join(instance.path_page_paper, "%d.*" % instance.num_page)
		ret = subprocess.call(cmd.split(" "))
		if ret:
			instance.print_activity("[FAIL %d] %s" % (ret, cmd))

	# Scan specific
	def search_scanner(self):
		return "plustek:libusb:001:014"

	# To avoid crushing existing paper waiting to be sorted in path_paper
	def get_number_paper_to_sort(self):
		paper_list = []
		for root, directories, filenames in os.walk(self.path_paper):
			paper_list.extend(filenames)
		max_number = 0
		for f in paper_list:
			filename = f.split("/")[-1]
			cur_number = int(re.findall(r'\d+', filename)[0])
			if (cur_number > max_number):
				max_number = cur_number
		
		return max_number

	def print_activity(self, stra):
		self.str_activity = stra

	def scan(self):
		self.print_activity("Scanning page %d..." % (self.num_page + 1))

		pnm = os.path.join(self.path_page_paper, "%d.pnm" % (self.num_page + 1))
		with open(pnm, "w") as f:
			# Effective scan.
			cmd = "scanimage -d %s --res 300 --format pnm -x 215 -y 297 --warmup-time 1" % self.search_scanner()
			res = subprocess.call(cmd.split(" "), stdout = f)
			if (res != 0):
				self.print_activity("\"%s\" failed.\n" % cmd)
				return 1

			# Convert to jpg, way faster to display.
			jpg = os.path.join(self.path_page_paper, "%d.jpg" % (self.num_page + 1))
			cmd = "convert -scale 25%% %s %s" % (pnm, jpg)
			ret = subprocess.call(cmd.split(" "))
			if ret:
				self.print_activity("[FAIL %d] %s" % (ret, cmd))
				return 1

			# Scan success.
			self.print_activity("Scanned page %d." % (self.num_page + 1))
			self.num_page_scanned_inc(0)
		        
		return 0

	def scan_top(instance, value):
		if (instance.num_page < instance.nb_page):
			ret = instance.scan()
			if ret:
				return
			instance.num_page_inc(value)
		elif (instance.num_page == instance.nb_page):
	                # Get the number of papers waiting to be sorted.		
			nb_paper_to_sort = instance.get_number_paper_to_sort() + 1
			if (instance.nb_page == 1):
				cmd = "cp %s %s" % (os.path.join(instance.path_page_paper, "1.pnm"),
                                                    os.path.join(instance.path_paper, "scan_and_sort%d.tmp" % nb_paper_to_sort))
				ret = subprocess.call(cmd.split(" "))
				if (ret):
					instance.print_activity("[FAIL %d] %s.\n" % (ret, cmd))
			else:
				cmd = "convert "
				for i in range(1, instance.nb_page + 1):
					cmd += os.path.join(instance.path_page_paper, "%d.pnm " % i)
				cmd += "-append %s" % os.path.join(instance.path_paper, "scan_and_sort%d.tmp" % nb_paper_to_sort)
				ret = subprocess.call(cmd.split(" "))
                if (ret):
                	instance.print_activity("[FAIL %d] %s.\n" % (ret, cmd))

            # New paper
			instance.new_paper(value)

	def launch_scan(instance, value):
		# Wait for scan thread to finish before launching another one.
		if (instance.th_scan != None):
			instance.th_scan.join()

		# Create thread that handles scan/convert
		instance.th_scan = Thread(instance.scan_top(value))#ThreadScan(instance)
		instance.th_scan.start()
		

class ScanAndSortApp(App):
	window_layout = None

	def exit_app(*largs):
		kivy_app.stop()

	def build(self):
		# TODO give external callbacks.
		self.paper = PaperScanAndSort(	update_num_page = self.update_num_page,
										update_num_page_scanned = self.update_num_page_scanned,
										update_nb_page = self.update_nb_page,
										update_activity = self.update_activity)

		# Left side.
		left_layout = BoxLayout(orientation = 'vertical', size_hint = (.1, 1))
		btn_up_page = Button(text = "UP", size_hint = (1, .3), font_size = '25sp')
		btn_up_page.bind(on_press = self.paper.num_page_inc)
		btn_down_page = Button(text = "DOWN", size_hint = (1, .3), font_size = '25sp')
		btn_down_page.bind(on_press = self.paper.num_page_dec)
		left_layout.add_widget(btn_up_page)
		left_layout.add_widget(btn_down_page)

		# Middle.
		middle_layout = BoxLayout(orientation = 'vertical', size_hint = (.7, 1))
		self.img_page = Image(source = "", size_hint = (1, .95))
		self.lbl_activity = Label(text = "", size_hint = (1, .05))
		middle_layout.add_widget(self.img_page)
		middle_layout.add_widget(self.lbl_activity)

		# Right side.
		right_layout = BoxLayout(orientation = 'vertical', size_hint = (.2, 1))
		btn_plus = Button(text = "+", font_size = '25sp')
		btn_plus.bind(on_press = self.paper.nb_page_inc)
		btn_minus = Button(text = "-", font_size = '25sp')
		btn_minus.bind(on_press = self.paper.nb_page_dec)
		self.lbl_nb_num_page = Label(text = "0 / 1", font_size = '25sp')
		self.btn_accept = Button(text = "Scan", font_size = '25sp')
		self.btn_accept.bind(on_press = self.paper.launch_scan)
		self.btn_cancel_page = Button(text = "Rescan page", font_size = '25sp')
		self.btn_cancel_page.bind(on_press = self.paper.cancel_page)
		self.btn_cancel_paper = Button(text = "Cancel", font_size = '25sp')
		self.btn_cancel_paper.bind(on_press = self.paper.new_paper)

		right_layout.add_widget(btn_plus)
		right_layout.add_widget(self.lbl_nb_num_page)
		right_layout.add_widget(btn_minus)
		right_layout.add_widget(self.btn_accept)
		right_layout.add_widget(self.btn_cancel_page)
		right_layout.add_widget(self.btn_cancel_paper)

		self.window_layout = BoxLayout(orientation = 'horizontal', spacing = 10, padding = 10)
		self.window_layout.add_widget(left_layout)
		self.window_layout.add_widget(middle_layout)
		self.window_layout.add_widget(right_layout)

		Window.bind(on_close = self.exit_app)
		return self.window_layout
	
	# Helpers for callbacks.
	def update_str_btn_accept(self, instance, value):
		if (instance.num_page_scanned == 0):
			self.btn_accept.text = "Scan"
		elif (instance.num_page_scanned < instance.nb_page):
			self.btn_accept.text = "OK, scan next"
		elif (instance.num_page_scanned == instance.nb_page):
			self.btn_accept.text = "OK !"

	def update_lbl_nb_num_page(self, instance, value):
		self.lbl_nb_num_page.text = "%d / %d" % (instance.num_page, instance.nb_page)

	# Callbacks from PaperScanAndSort 
	def update_nb_page(self, instance, value):
		# Update label
		self.update_lbl_nb_num_page(instance, value)

	def update_num_page(self, instance, value):
		# Update label
		self.update_lbl_nb_num_page(instance, value)
		# Update image
		if (instance.num_page):
			self.img_page.source = os.path.join(instance.path_page_paper, "%d.jpg" % instance.num_page)
		else:
			self.img_page.source = ""
		self.img_page.reload()
	
 	def update_num_page_scanned(self, instance, value):
		# Update image
		if (instance.num_page_scanned):
			self.img_page.source = os.path.join(instance.path_page_paper, "%d.jpg" % instance.num_page_scanned)
		else:
			self.img_page.source = ""
		self.img_page.reload()
		# Update button
		self.update_str_btn_accept(instance, value)

	def update_activity(self, instance, value):
		# Update label activity 
		self.lbl_activity.text = instance.str_activity
		print(instance.str_activity)


if __name__ == "__main__":
	kivy_app = ScanAndSortApp()
	kivy_app.run()

