#!/bin/bash

SCAN_PAPER_SRC="/disk/owncloud/AlexGhiti/files/common/papers/"

$PWD/paper.py --scan_paper_src=$SCAN_PAPER_SRC &
$PWD/frontend/python_gui/scan_and_sort.py -- --scan_paper_src=$SCAN_PAPER_SRC &
