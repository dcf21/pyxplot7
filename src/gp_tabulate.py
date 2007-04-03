# GP_TABULATE.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id: $
#
# PyXPlot is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# You should have received a copy of the GNU General Public License along with
# PyXPlot; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

# ----------------------------------------------------------------------------

# Implementation of tabulate command

import gp_datafile
import gp_settings
import gp_math
import gp_version

import os
import sys
from math import *
import glob
import operator
import exceptions
import re


# Counters used to cycle plot styles
withstate = 0 # State parameter used when processing input after the word "with"

# Only warn user once about the using modifier when plotting functions
using_use_warned = False

# DIRECTIVE_TABULATE(): Handles the 'tabulate' command

def directive_tabulate(command,vars,funcs,settings):
  # Get the axes sorted out first
  axes = { 'x':{}, 'y':{}, 'z':{} } 
  for dir in ['x', 'y']:
   axes[dir][1] = gp_settings.axes[dir][1].copy()

  # Apply the changes that the user asked for
  for i in range(min(1, len(command['range_list']))):
   if ((i%2) == 0): direction='x'
   else           : direction='y'
   number=int(i/2)+1
   if 'min' in command['range_list'][i]: axes[direction][number]['MIN'] = command['range_list'][i]['min']
   if 'max' in command['range_list'][i]: axes[direction][number]['MAX'] = command['range_list'][i]['max']
   

  # Step 1: Work out the ranges of the data, to decide how to autoscale.
  #         This is achieved with a dry-run of the plotting process.
  any_autoscaling_axes = 0
  for direction in 'x', 'y':
   number = 1
   axis = axes[direction][number]
   axis['MIN_USED'] = axis['MIN']
   axis['MAX_USED'] = axis['MAX']
   axis['AXIS']     = None
   axis['LINKINFO'] = {}
   if (axis['LOG'] == "ON"):
    if (axis['MIN_USED'] != None) and (axis['MIN_USED'] <= 0.0):
     axis['MIN_USED'] = None
     axis['MIN'] = None
     gp_warning("Warning: Log axis %s%d set with range minimum < 0 -- this is impossible, so autoscaling instead."%(direction,number))
    if (axis['MAX_USED'] != None) and (axis['MAX_USED'] <= 0.0):
     axis['MAX_USED'] = None
     axis['MAX'] = None
     gp_warning("Warning: Log axis %s%d set with range maximum < 0 -- this is impossible, so autoscaling instead."%(direction,number))

   if ((axis['MIN_USED'] == None) or (axis['MIN_USED'] == None)):
    any_autoscaling_axes = 1

  # Deal with any other user-supplied details

  # Read datafile filename
  if 'filename' in command:
   datafile = command['filename']
  else:
   functions = [item['expression'] for item in command['expression_list:'] ]

  # every
  if 'every_list:' in command: every = command['every_list:']
  else                       : every = []

  # index
  if 'index' in command: index = int(command['index'])
  else                 : index = -1 # default

  # select
  if 'select_criterion' in command: select_criteria = command['select_criterion']
  else                            : select_criteria = ''

  # Using rows or columns
  if   'use_rows'    in command: usingrowcol = "row"
  elif 'use_columns' in command: usingrowcol = "col"
  else                         : usingrowcol = "col" # default

  # using
  if 'using_list:' in command: using = [item['using_item'] for item in command['using_list:']]
  else                       : using = []


  if 'filename' in command:
   # Obtain file data straight away
   datagrid = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, every, vars, funcs, "points", True, None)
  else: # Deal with tabulating functions
   # Automatic range choices
   if (axes['x'][1]['MIN'] == None):
    if (axes['x'][1]['LOG'] == 'ON'):
     if (axes['x'][1]['MAX'] != None): axes['x'][1]['MIN'] = axes['x'][1]['MAX'] / 100 # Log axes start from 1
     else                : axes['x'][1]['MIN'] = 1.0
    else:
     if (axes['x'][1]['MAX'] != None): axes['x'][1]['MIN'] = maximum - 20
     else                : axes['x'][1]['MIN'] = -10.0         # Lin axes start from -10
   if (axes['x'][1]['MAX'] == None):
    if (axes['x'][1]['LOG'] == 'ON'): axes['x'][1]['MAX'] = axes['x'][1]['MIN'] * 100
    else                                             : axes['x'][1]['MAX'] = axes['x'][1]['MIN'] + 20

   # Obtain a raster
   if (axes['x'][1]['LOG'] == 'ON'): xrast = gp_math.lograst(axes['x'][1]['MIN'], axes['x'][1]['MAX'], settings['SAMPLES'])
   else:                                              xrast = gp_math.linrast(axes['x'][1]['MIN'], axes['x'][1]['MAX'], settings['SAMPLES'])
   
   # Obtain the data grid
   datagrid = gp_datafile.gp_function_datagrid(xrast, functions, 'x', usingrowcol, using, select_criteria, every, vars, funcs, 'points', True, None)

  
  # Filter the data that we've got
  datagrid = filter_dataset(datagrid, axes)

  # Print the data out
  output_table(datagrid, settings)

# FILTER_DATASET(): Filter data against the ranges supplied

def filter_dataset (datagrid, axes):
 newgrid = []
 for [rows, cols, block] in datagrid[1:]: # We do not want the initial grid with all the points in
  newblock = []
  for line in block:
   x = line[0]
   if (x < axes['x'][1]['MIN'] or (axes['x'][1]['MAX'] != None and x > axes['x'][1]['MAX'])):
    rows -= 1
   else:
    newblock.append(line)
  newgrid.append([rows, cols, newblock])
 return newgrid

# OUTPUT_TABLE(): Write the table of numbers produced out to a file

def output_table (datagrid, settings):
  # Get the filename
  fname_out = os.path.expanduser(settings['OUTPUT'])
  if (fname_out == ""): fname_out = "pyxplot.dat"
  out_fname = os.path.join(gp_settings.cwd, os.path.expanduser(fname_out))

  f = open(out_fname, 'a')

  # Write a header
  f.write("# Datafile produced by by PyXPlot\n")

  # Produce an optimal format string using much jiggery-pokery
  cols = datagrid[0][1]
  allints  = [True for i in range(cols)]
  allsmall = [True for i in range(cols)]
  for [rows, cols, block] in datagrid:
   for line in block:
    for i in range(cols):
     if (line[i] != float(int(line[i]))):
      allints[i] = False
     if (abs(line[i]) >= 1000 or (abs(line[i]) < .0999999 and line[i] != 0.)):
      allsmall[i] = False
  formats = []
  for i in range(cols):
   if (allints[i]):
    formats.append("%10d")
   elif (allsmall[i]):
    formats.append("%11f")
   else:
    formats.append("%15e")

  # Actually write the data file
  for [rows, cols, block] in datagrid:
   for line in block:
    strs = []
    for i in range(len(line)):
     format = formats[i]
     strs.append(formats[i]%line[i])
    str = ' '.join(strs)
    f.write("%s\n"%str)

  f.close()
  return
