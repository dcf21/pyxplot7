# GP_SPLINE.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
#
# $Id$
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

import gp_eval
import gp_datafile
import gp_math
from gp_autocomplete import *
from gp_error import *

import sys
import re
import operator
from math import *

try: import scipy.interpolate
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

# DIRECTIVE_SPLINE(): Implements the "spline" directive

def directive_spline(command, vars):

  assert not SCIPY_ABSENT, "The use of cubic splines requires the scipy module for python, which is not installed. Please install and try again."

  # FIRST OF ALL, READ THE INPUT PARAMETERS FROM THE COMMANDLINE

  # Ranges
  ranges = []
  for drange in command['range_list']:
   if 'min' in drange.keys(): range_min = drange['min']
   else                     : range_min = None
   if 'max' in drange.keys(): range_max = drange['max']
   else                     : range_max = None
   ranges.append([ range_min , range_max ])

  # Function name
  funcname = command['fit_function']

  # Read datafile filename
  datafile = command['filename']

  # every
  if 'every_list:' in command: every = command['every_list:']
  else                       : every = []

  # index
  if 'index' in command: index = int(command['index'])
  else                 : index = -1 # default

  # select
  if 'select_criterion' in command: select_criteria = command['select_criterion']
  else                            : select_criteria = ''
  select_cont = True
  if (('select_cont' in command) and (command['select_cont'][0] == 'd')):
   select_cont = False

  # smooth
  if 'smooth' in command: smoothing = float(command['smooth'])
  else                  : smoothing = 0.0

  # Using rows or columns
  if   'use_rows'    in command: usingrowcol = "row"
  elif 'use_columns' in command: usingrowcol = "col"
  else                         : usingrowcol = "col" # default

  # using
  if 'using_list:' in command: using = [item['using_item'] for item in command['using_list:']]
  else                       : using = []

  # We have now read all of our commandline parameters, and are ready to start spline fitting
  try:
   (rows,columns,datagrid) = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, select_cont, every, vars, "points")[0]
  except KeyboardInterrupt: raise
  except:
   gp_error("Error reading input datafile:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return # Error

  if (rows == 0):
   gp_error("Error: empty data file %s provided to the spline command"%datafile)
   return # Error

  try:
   splineobj = make_spline_object(rows, columns, datagrid, smoothing, ranges)[2]
   funcs[funcname] = [-1, [[datafile, splineobj]]]
  except KeyboardInterrupt: raise
  except:
   gp_error("Error processing input datafile:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  return # Done

# MAKE_SPLINE_OBJECT(): Makes a scipy spline object

def make_spline_object(rows,columns,datagrid,smoothing=0.0,ranges=[]):

 assert not SCIPY_ABSENT, "The use of cubic splines requires the scipy module for python, which is not installed. Please install and try again."

 if   (columns == 2): yerrors = 0
 elif (columns == 3): yerrors = 1
 else               : raise ValueError, "spline command needs two or three columns of input data; %d supplied."%columns

 # Sort data points into list
 datagrid.sort(gp_math.sort_on_first_list_item)
 xmin = datagrid[ 0][0]
 xmax = datagrid[-1][0]

 # If we have no errors supplied, work out standard deviation of data, to make smoothing behave sensibly
 if (yerrors != 1):
  sum_n = 0.0 ; sum_y = 0.0 ; sum_y2 = 0.0
  for datapoint in datagrid:
   sum_n  += 1.0
   sum_y  += datapoint[1]
   sum_y2 += datapoint[1] ** 2
  standev = sqrt(sum_y2/sum_n - (sum_y/sum_n)**2)
 else:
  standev = 0.0

 x_list = [] ; y_list = [] ; w_list = []
 datagrid_cpy = [x_list, y_list, w_list]
 xprev = None
 multivalue_warned = False
 for datapoint in datagrid:
  if (datapoint[0] == xprev): # Filter out repeat datapoint
    if not multivalue_warned:
      gp_warning("Warning: Data supplied for spline appears to be multivalued. For example, there are multiple values supplied at x=%s. Result may not be as expected."%xprev)
      multivalue_warned = True
    continue
  if ((0 < len(ranges)) and (((ranges[0][0] == None) or (ranges[0][0] > datapoint[0])) or ((ranges[0][1] == None) or (ranges[0][1] < datapoint[0])))): continue
  if ((1 < len(ranges)) and (((ranges[1][0] == None) or (ranges[1][0] > datapoint[1])) or ((ranges[1][1] == None) or (ranges[1][1] < datapoint[1])))): continue
  datagrid_cpy[0].append(datapoint[0])
  datagrid_cpy[1].append(datapoint[1])
  if (yerrors == 1): weight = datapoint[2] # Units of standard deviation ; actually 1/weight
  else             : weight = standev/10
  weight = max(weight,1e-200) # Minimum inverse weight is 1e-200, since we're about to find one over it for weight
  datagrid_cpy[2].append(1.0/weight)
  xprev = datapoint[0]
 assert (len(x_list) > 3), "Need at least four datapoints to fit a cubic-spline"
 return [xmin, xmax, scipy.interpolate.splrep(x=x_list, y=y_list, w=w_list, s=(float(smoothing)*(len(datagrid_cpy[0])-sqrt(2.0*len(datagrid_cpy[0])))) )] # nest=(len(datagrid_cpy[0])+5) used to be here

# SPLINE_EVALUATE(): Evaluate a spline at point x (This is just a wrapper for scipy)

def spline_evaluate(x, splineobj):
 assert not SCIPY_ABSENT, "The use of cubic splines requires the scipy module for python, which is not installed. Please install and try again."
 return scipy.interpolate.splev(x, splineobj, der=0)
