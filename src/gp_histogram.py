# GP_HISTOGRAM.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-8 Dominic Ford <coders@pyxplot.org.uk>
#               2008   Ross Church
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
import gp_userspace
from gp_error import *

import sys
from math import *

# DIRECTIVE_HISTOGRAM(): Implements the "histogram" directive

def directive_histogram(command, vars, settings):
  
  # Read ranges from RE++ input
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
   (rows,columns,datagrid) = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, True, every, vars, "points")[0]
  except KeyboardInterrupt: raise
  except:
   gp_error("Error reading input datafile:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return # Error

  # Check for a blank dataset
  if (datagrid == []):
   gp_warning("Warning: No data provided to histogram command!")
   gp_userspace.gp_function_declare("%s(x) = 0."%funcname)
   return

  # Sort data points into a list in order of x-axis value
  datagrid.sort(gp_math.sort_on_second_list_item)
  xmin = datagrid[ 0][1]
  xmax = datagrid[-1][1]

  # Now we need to work out our bins
  # Precedence: 1. Set of bins listed on command line
  #             2. Binwidth,origin listed on command line (Unimplemented)
  #             3. Set of bins set as a setting 
  #             4. Binwidth,origin set as a setting

  if ('bin_list,' in command):
   bins = []
   for x in command['bin_list,']:
    bins.append(x['x'])

  else:
   if ('binwidth' in command)  : binwidth  = command['binwidth']
   else                        : binwidth  = settings['BINWIDTH']
   assert (binwidth > 0.0), "Width of histogram bins must be greater than zero"
   if ('binorigin' in command) : binorigin = command['binorigin']
   else                        : binorigin = settings['BINORIGIN']
   bins = get_bins(ranges, xmin, xmax, binwidth, binorigin)
  
  # Check for user-specified data ranges to consider
  binrange = [xmin, xmax]
  if (len(ranges) > 0):
   if (ranges[0][0] != None): binrange[0] = ranges[0][0]
   if (ranges[0][1] != None): binrange[1] = ranges[0][1]

  counts = histcount(bins, datagrid, binrange)    # Bin the data up
  make_histogram_function(datafile, funcname, bins, counts) # Turn the binned data into a function
  return

# MAKE_HISTOGRAM_FUNCTION(): Turn binned up histogram data into a function
# To accomplish this we call the internal spliced function creation routine
# Hic draconis

def make_histogram_function(filename, funcname, bins, counts):
  # See if the function already exists as a variable and delete it if it does
  assert funcname not in gp_userspace.math_functions.keys(), "Cannot re-define a core mathematical function."
  if funcname in gp_userspace.variables: del gp_userspace.variables[funcname]

  # First set the function to be zero everywhere
  gp_userspace.gp_function_declare("%s(x) = "%funcname)
  gp_userspace.gp_function_declare("%s(x) = 0."%funcname)

  # Then iterate through each of the bins
  for i in range(1,len(bins)):
   if (counts[i] == 0): continue
   gp_userspace.gp_function_declare( "%s(x) [%f:%f] = %f"%(funcname,bins[i-1],bins[i],counts[i]) )
  gp_userspace.functions[funcname]['histogram']=True
  gp_userspace.functions[funcname]['fname']=filename
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
# supplied in bins[]. Returns a list such that counts[i] is the number of items
# with bins[i-1]<x<bins[i]

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

  # Divide by width of bins to obtain an histogram
  for i in range(1,len(bins)):
   counts[i] = float(counts[i]) / float(bins[i]-bins[i-1])
  return counts

# HISTRAST(): Generate a raster suitable for plotting a histogram, consisting of a single point at the centre of each box

def histrast(minimum, maximum, logscale, funcname):
 ranges = []  # List of all the ranges for which the histogram function has a bin defined
 raster = []
 for definition in gp_userspace.functions[funcname]['defn']:
  ranges.append(definition['ranges'][0])
 
 if (logscale == 'ON'):    # We are plotting the histogram on a logrithmic scale
  for range in ranges:
   if (range[0] == None): continue
   minr = float(min(range))
   maxr = float(max(range))
   if (minr <= 0): continue   # Skip bins that extend beyond x=0
   raster.append(sqrt(minr*maxr))
 else:  # linear scale
  for range in ranges:
   if (range[0] == None): continue
   minr = float(min(range))
   maxr = float(max(range))
   raster.append(0.5*(minr+maxr))
 return raster
