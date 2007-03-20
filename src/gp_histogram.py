# GP_HISTOGRAM.PY
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

import gp_eval
import gp_datafile
import gp_math
from gp_error import *

import sys
from math import *

# DIRECTIVE_HISTOGRAM(): Implements the "histogram" directive

def directive_histogram(command, vars, funcs, settings):
  
  # First we need to get our data, so we use gp_datafile
  # Ranges
  ranges = []
  for drange in command['range_list']:
   if 'min' in drange.keys(): range_min = drange['min']
   else                     : range_min = None
   if 'max' in drange.keys(): range_max = drange['max']
   else                     : range_max = None
   ranges.append([ range_min , range_max ])

  # Function name
  funcname = command['hist_function']

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

  # Using rows or columns
  if   'use_rows'    in command: usingrowcol = "row"
  elif 'use_columns' in command: usingrowcol = "col"
  else                         : usingrowcol = "col" # default

  # using
  if 'using_list:' in command: using = [item['using_item'] for item in command['using_list:']]
  else                       : using = ['1']

  if (len(using) > 1):
   raise ValueError, "histogram command needs 1 column of input data; %d supplied."%len(using)

  # We have now read all of our commandline parameters, and are ready to get the data
  try:
   (rows,columns,datagrid) = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, every, vars, funcs, "points")[0]
  except KeyboardInterrupt: raise
  except:
   gp_error("Error reading input datafile:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return # Error

  # Sort data points into list
  datagrid.sort(gp_math.sort_on_second_list_item)
  xmin = datagrid[ 0][1]
  xmax = datagrid[-1][1]

  # Now we need to work out our bins
  # Precedence: 1. Set of bins listed on command line
  #             2. Binwidth,origin listed on command line
  #             (Unimplemented) 3. Set of bins set as a setting 
  #             4. Binwidth,origin set as a setting

  if ('bin_list,' in command):
   bins = []
   for x in command['bin_list,']:
    bins.append(x['x'])

  elif ('binwidth' in command or 'binorigin' in command):
   if ('binwidth' in command)  : binwidth  = command['binwidth']
   else                        : binwidth  = settings['BINWIDTH']
   if ('binorigin' in command) : binorigin = command['binorigin']
   else                        : binorigin = settings['BINORIGIN']
   bins = get_bins(ranges, xmin, xmax, binwidth, binorigin)
  
  # (Unimplemented) elif (settings['BINS'] != None):
  else:
   binwidth = settings['BINWIDTH']
   binorigin = settings['BINORIGIN']
   bins = get_bins(ranges, xmin, xmax, binwidth, binorigin)

  # Check for user-specified data ranges to consider
  binrange = [xmin, xmax]
  if (len(ranges) > 0):
   if (ranges[0][0] != None):
    binrange[0] = ranges[0][0]
   if (ranges[0][1] != None):
    binrange[1] = ranges[0][1]

  # Bin the data up
  counts = histcount(bins, datagrid, binrange)

  # Turn the binned data into a function
  make_histogram_function(funcname, bins, counts, funcs)

  return

# MAKE_HISTOGRAM_FUNCTION(): Turn binned up histogram data into a function
# To accomplish this we call the internal spliced function creation routine
# Hic draconis

def make_histogram_function(funcname, bins, counts, funcs):
  # See if the function already exists and delete it if it does
  if (funcname in funcs):
   gp_eval.gp_function_declare("%s(x) = "%funcname, funcs)

  # First set the function to be zero everywhere
  line = "%s(x) = 0."%funcname
  gp_eval.gp_function_declare(line, funcs)

  # Then iterate through each of the bins
  for i in range(1,len(bins)):
   if (counts[i] == 0): 
    continue
   line = "%s(x) [%f:%f] = %d"%(funcname,bins[i-1],bins[i],counts[i])
   gp_eval.gp_function_declare(line, funcs)
   
  return

# GET_BINS(): Get set of bins for histogram

def get_bins(ranges, xmin, xmax, binwidth, binorigin):

# If we have limits to where we're binning data from then there's no point in considering data outside it.
  if (len(ranges)==0):
   xbinmin = xmin
   xbinmax = xmax
  else:
   if (ranges[0][0] == None):
    xbinmin = xmin
   else:
    xbinmin = ranges[0][0]
   if (ranges[0][1] == None):
    xbinmax = xmax
   else:
    xbinmax = ranges[0][1]

  # Turn the bin origin setting into something more useful
  binorigin -= binwidth*floor(binorigin/binwidth)

  # Expand the ends of the outside bins to match the provided bin pattern
  xbinmin = floor((xbinmin-binorigin)/binwidth)*binwidth + binorigin
  xbinmax = ceil((xbinmax-binorigin)/binwidth)*binwidth + binorigin
  Nbins = (int)((xbinmax-xbinmin)/binwidth) + 1

  bins = [i*binwidth+xbinmin for i in range(Nbins)]
  
  return bins
  

# HISTCOUNT(): Produce counts with which to plot a histogram, into the bins 
# supplied in bins[]

# Returns a list such that counts[i] is the number of items with 
# bins[i-1]<x<bins[i]

def histcount(bins, datagrid, binrange):
  counts = [0]*(len(bins))
  for datum in datagrid:
   x = datum[1]
   # Check that we're within the ranges
   if ((x<binrange[0]) or (x>binrange[1])):
    continue

   # Check all the bins and insert into the correct one
   for i in range(len(bins)):
    if (x<=bins[i]):
     counts[i]+=1
     break
  counts[0] = 0
  return counts
