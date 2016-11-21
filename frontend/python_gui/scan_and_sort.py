#!/usr/bin/env python

import os
import re
import pyinotify
import argparse
import datetime
from git import Git, Repo, Head, exc
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
	scanner_name = "plustek:libusb:002:009"
	# ObjectProperty
	nb_page = NumericProperty(1)
	num_page = NumericProperty(0)
	# Attributes linked to a GUI object.
	str_lbl_nb_num_page = '' 

	def __init__(self, *args, **kwargs):
		super(PaperScanAndSort, self).__init__(*args, **kwargs)
		# Retrieve App object to deal with auto-refreshing of
		# GUI objects. TODO ask if this the right way to do ?
		self.app = kwargs["app"]
		# TODO Add a label for the path
		self.path = "/tmp"
		self.str_lbl_nb_num_page = "%d / %d" % (self.num_page, self.nb_page)
		self.bind(nb_page = self.update_nb_num_page)
		self.bind(num_page = self.update_nb_num_page)

	def nb_page_inc(instance, value):
		instance.nb_page += 1

	def nb_page_dec(instance, value):
		if (instance.nb_page > 1):
			instance.nb_page -= 1

	# ObjectProperty callbacks.
	def update_nb_num_page(self, instance, value):
		self.str_lbl_nb_num_page = "%d / %d" % (self.num_page, self.nb_page)
		instance.app.lbl_nb_num_page.text = self.str_lbl_nb_num_page


class ScanAndSortApp(App):
	window_layout = None

	def exit_app(*largs):
		kivy_app.stop()

	def build(self):
		self.paper = PaperScanAndSort(app = self)

		# Left side.
		left_layout = BoxLayout(orientation = 'vertical', size_hint = (.1, 1))
		btn_up_page = Button(text = "UP", size_hint = (1, .3), font_size = '40sp')
		btn_down_page = Button(text = "DOWN", size_hint = (1, .3), font_size = '40sp')
		left_layout.add_widget(btn_up_page)
		left_layout.add_widget(btn_down_page)

		# Middle.
		img = Image(source="/nfs/home/aghiti/Projects/sort_scan_image/frontend/python_gui/Facture_30082106_214400.png",
					size_hint = (.7, 1))

		# Right side.
		right_layout = BoxLayout(orientation = 'vertical', size_hint = (.2, 1))
		btn_plus = Button(text = "+", font_size = '40sp')
		btn_plus.bind(on_press = self.paper.nb_page_inc)
		btn_minus = Button(text = "-", font_size = '40sp')
		btn_minus.bind(on_press = self.paper.nb_page_dec)
		self.lbl_nb_num_page = Label(text = self.paper.str_lbl_nb_num_page, font_size = '40sp')
		btn_accept = Button(text = "OK", font_size = '40sp')
		right_layout.add_widget(btn_plus)
		right_layout.add_widget(self.lbl_nb_num_page)
		right_layout.add_widget(btn_minus)
		right_layout.add_widget(btn_accept)

		self.window_layout = BoxLayout(orientation = 'horizontal', spacing = 10, padding = 10)
		self.window_layout.add_widget(left_layout)
		self.window_layout.add_widget(img)
		self.window_layout.add_widget(right_layout)

		Window.bind(on_close = self.exit_app)
		return self.window_layout


if __name__ == "__main__":
	kivy_app = ScanAndSortApp()
	kivy_app.run()

