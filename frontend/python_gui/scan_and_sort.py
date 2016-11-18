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

Config.set('graphics', 'fullscreen', 1)

class PaperScanAndSort():
	def __init__(self):
		self.path = "/tmp"
		# NumBer of pages in paper
		self.nb_page = 1
		# NUMber of the page being displayed
		self.num_page = 0


class ScanAndSortApp(App):
	window_layout = None

	def exit_app(*largs):
		kivy_app.stop()

	def build(self):
		self.paper = PaperScanAndSort()

		left_layout = BoxLayout(orientation = 'vertical', size_hint = (.1, 1))
		btn_up_page = Button(text = "UP", size_hint = (1, .3), font_size = '40sp')
		btn_down_page = Button(text = "DOWN", size_hint = (1, .3), font_size = '40sp')
		left_layout.add_widget(btn_up_page)
		left_layout.add_widget(btn_down_page)

		img = Image(source="/nfs/home/aghiti/Projects/sort_scan_image/frontend/python_gui/Facture_30082106_214400.png",
					size_hint = (.7, 1))

		right_layout = BoxLayout(orientation = 'vertical', size_hint = (.2, 1))
		btn_plus = Button(text = "+", font_size = '40sp')
		btn_minus = Button(text = "-", font_size = '40sp')
		lbl_nb_page = Label(text = "%d / %d" % (self.paper.num_page, self.paper.nb_page), font_size = '40sp')
		btn_accept = Button(text = "OK", font_size = '40sp')
		right_layout.add_widget(btn_plus)
		right_layout.add_widget(lbl_nb_page)
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

