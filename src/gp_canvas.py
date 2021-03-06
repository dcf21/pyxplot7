# GP_CANVAS.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-9 Dominic Ford <coders@pyxplot.org.uk>
#               2008-9 Ross Church
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

# Implementation of plot command

import gp_settings
from gp_autocomplete import *
from gp_error import *
import gp_plot

import os
import sys
from math import *
import re
from dcfpyx import *

# Store list of previously plotted items from last 'plot' command. This is used to replot; not part of multiplot.
plotlist = []
axes_this = { 'x':{}, 'y':{}, 'z':{} } # This is global so that set xlabel commands can influence replotting

# List of items plotted on our multiplot
multiplot_plotdesc  = []
replot_focus        = None

# PLOTORDER_CLEAR(): Clear all items from plot order

def plotorder_clear():
 global multiplot_plotdesc, replot_focus
 multiplot_plotdesc  = [] # Wipe the plotting canvas
 replot_focus        = None

# DIRECTIVE_LIST(): List all items on a multiplot

def directive_list():
 any_deleted=False
 gp_report("#  ID | Command")
 for item in multiplot_plotdesc:
  if item['deleted']=='ON':
   line="d"
   any_deleted=True
  else:
   line=" "
  line += "%4d   "%item['number']
  line += item['listdesc']
  gp_report(line)
 if any_deleted:
  gp_report("\n# Items marked 'd' are deleted")

# DIRECTIVE_TEXT(): Handles the 'text' command

def directive_text(command,commandtext,linestyles,vars,settings,interactive):
 if (gp_settings.settings_global['MULTIPLOT'] != 'ON'): plotorder_clear()

 title = command['string']

 if 'x'        in command: x = command['x']
 else                    : x = 0.0
 if 'y'        in command: y = command['y']
 else                    : y = 0.0
 if 'rotation' in command: rotation = command['rotation']
 else                    : rotation = 0.0
 if 'colour'   in command: colour = command['colour']
 else                    : colour = settings['TEXTCOLOUR']

 this_plotdesc = {'itemtype':'text',
                  'number'  :len(multiplot_plotdesc),
                  'text'    :title,
                  'x_pos'   :x,
                  'y_pos'   :y,
                  'settings':settings.copy(),
                  'deleted' :'OFF',
                  'rotation':rotation,
                  'colour':colour,
                  'listdesc':commandtext
                  }
 multiplot_plotdesc.append(this_plotdesc)

 if (gp_settings.settings_global['MULTIPLOT'] == 'ON') and interactive:
  gp_report("Text label added to multiplot with reference %d."%this_plotdesc['number'])

 if (gp_settings.settings_global['DISPLAY'] == "ON"):
  try:
   unsuccessful_plot_operations = gp_plot.multiplot_plot(linestyles,vars,settings,multiplot_plotdesc)
  except KeyboardInterrupt: raise
  except:
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return

  if (gp_settings.settings_global['MULTIPLOT'] == 'ON'):
   if (this_plotdesc['number'] in unsuccessful_plot_operations) and (gp_settings.settings_global['DISPLAY'] == "ON"):
    multiplot_plotdesc.pop()
    if interactive:
     gp_report("Text label has been removed from multiplot, because it generated an error.")

# DIRECTIVE_ARROW(): Handles the 'arrow' command

def directive_arrow(command,commandtext,linestyles,vars,settings,interactive):
 if (gp_settings.settings_global['MULTIPLOT'] != 'ON'): plotorder_clear()
 
 x0 = command['x1'] ; y0 = command['y1']
 x1 = command['x2'] ; y1 = command['y2']

 this_plotdesc = {'itemtype':'arrow',
                  'number'  :len(multiplot_plotdesc),
                  'x_pos'   :x0,
                  'y_pos'   :y0,
                  'x2_pos'  :x1,
                  'y2_pos'  :y1,
                  'style'   :command,
                  'settings':settings.copy(),
                  'deleted' :'OFF',
                  'listdesc':commandtext
                  }
 multiplot_plotdesc.append(this_plotdesc)

 if (gp_settings.settings_global['MULTIPLOT'] == 'ON') and interactive:
  gp_report("Arrow added to multiplot with reference %d."%this_plotdesc['number'])

 if (gp_settings.settings_global['DISPLAY'] == "ON"):
  try:
   unsuccessful_plot_operations = gp_plot.multiplot_plot(linestyles,vars,settings,multiplot_plotdesc)
  except KeyboardInterrupt: raise
  except:
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return

  if (gp_settings.settings_global['MULTIPLOT'] == 'ON'):
   if (this_plotdesc['number'] in unsuccessful_plot_operations) and (gp_settings.settings_global['DISPLAY'] == "ON"):
    multiplot_plotdesc.pop()
    if interactive:
     gp_report("Arrow has been removed from multiplot, because it generated an error.")

# DIRECTIVE_JPEG(): Handles the 'jpeg' command

def directive_jpeg(command,commandtext,linestyles,vars,settings,interactive):
 if (gp_settings.settings_global['MULTIPLOT'] != 'ON'): plotorder_clear()

 filename = command['filename']
 if 'x'        in command: x = command['x']
 else                    : x = settings['ORIGINX']
 if 'y'        in command: y = command['y']
 else                    : y = settings['ORIGINY']
 if 'rotation' in command: rotation = command['rotation']
 else                    : rotation = 0.0
 if 'width'    in command: width  = command['width']
 else                    : width  = None
 if 'height'   in command: height = command['height']
 else                    : height = None

 this_plotdesc = {'itemtype':'jpeg',
                  'number'  :len(multiplot_plotdesc),
                  'filename':filename,
                  'x_pos'   :x,
                  'y_pos'   :y,
                  'deleted' :'OFF',
                  'rotation':rotation,
                  'width'   :width,
                  'height'  :height,
                  'listdesc':commandtext
                  }
 multiplot_plotdesc.append(this_plotdesc)

 if (gp_settings.settings_global['MULTIPLOT'] == 'ON') and interactive:
  gp_report("jpeg image added to multiplot with reference %d."%this_plotdesc['number'])

 if (gp_settings.settings_global['DISPLAY'] == "ON"):
  try:
   unsuccessful_plot_operations = gp_plot.multiplot_plot(linestyles,vars,settings,multiplot_plotdesc)
  except KeyboardInterrupt: raise
  except:
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return

  if (gp_settings.settings_global['MULTIPLOT'] == 'ON'):
   if (this_plotdesc['number'] in unsuccessful_plot_operations) and (gp_settings.settings_global['DISPLAY'] == "ON"):
    multiplot_plotdesc.pop()
    if interactive:
     gp_report("jpeg image has been removed from multiplot, because it generated an error.")

# DIRECTIVE_EPS(): Handles the 'eps' command

def directive_eps(command,commandtext,linestyles,vars,settings,interactive):
 if (gp_settings.settings_global['MULTIPLOT'] != 'ON'): plotorder_clear()

 filename = command['filename']
 if 'x'        in command: x = command['x']
 else                    : x = settings['ORIGINX']
 if 'y'        in command: y = command['y']
 else                    : y = settings['ORIGINY']
 if 'rotation' in command: rotation = command['rotation']
 else                    : rotation = 0.0
 if 'width'    in command: width  = command['width']
 else                    : width  = None
 if 'height'   in command: height = command['height']
 else                    : height = None

 this_plotdesc = {'itemtype':'eps',
                  'number'  :len(multiplot_plotdesc),
                  'filename':filename,
                  'x_pos'   :x,
                  'y_pos'   :y,
                  'deleted' :'OFF',
                  'rotation':rotation,
                  'width'   :width,
                  'height'  :height,
                  'listdesc':commandtext
                  }
 multiplot_plotdesc.append(this_plotdesc)

 if (gp_settings.settings_global['MULTIPLOT'] == 'ON') and interactive:
  gp_report("eps image added to multiplot with reference %d."%this_plotdesc['number'])

 if (gp_settings.settings_global['DISPLAY'] == "ON"):
  try:
   unsuccessful_plot_operations = gp_plot.multiplot_plot(linestyles,vars,settings,multiplot_plotdesc)
  except KeyboardInterrupt: raise
  except:
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return

  if (gp_settings.settings_global['MULTIPLOT'] == 'ON'):
   if (this_plotdesc['number'] in unsuccessful_plot_operations) and (gp_settings.settings_global['DISPLAY'] == "ON"):
    multiplot_plotdesc.pop()
    if interactive:
     gp_report("eps image has been removed from multiplot, because it generated an error.")

# DIRECTIVE_PLOT(): Handles the 'plot' command

def directive_plot(command,commandtext,linestyles,vars,settings,axes,labels,arrows,replot_stat,interactive):
  global plotlist, axes_this, replot_focus
  global multiplot_plotdesc

  x_position = settings['ORIGINX']
  y_position = settings['ORIGINY']

  if (gp_settings.settings_global['MULTIPLOT'] != 'ON'): plotorder_clear()

  if (replot_stat == 0): plotlist = [] # If not replotting, wipe plot list
  else:
   if (gp_settings.settings_global['MULTIPLOT'] == 'ON'): # If replotting a multiplot, wipe last graph
    if (replot_focus != None):
     x_position = multiplot_plotdesc[replot_focus]['settings']['ORIGINX'] # Plot may have been moved with the 'move' command
     y_position = multiplot_plotdesc[replot_focus]['settings']['ORIGINY']

  # Now make a local copy of axes, and store it in multiplot_plotdesc[n]['axes']
  # We need a copy, because user may change axis ranges in the plot command, overriding settings
  # in gp_settings lists of axes.
  if (replot_stat == 0): axes_this = { 'x':{},'y':{},'z':{} } # NB: replot on same axes as before when replotting, so do not clear axes_this
  for [direction,axis_list_to] in axes_this.iteritems():
   for [number,axis] in axes[direction].iteritems():
    if number not in axis_list_to:
     axis_list_to[number] = {'SETTINGS':axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}
     # 'AXIS' will become a PyX axis object in due course

  # Now read range specifications, modifying local copy of axes as required
  # NB: Any ranges that are set go into ['SETTINGS']['MIN/MAX'], not ['MIN_USED'] or ['MAX_USED']
  for i in range(len(command['range_list'])):
   if ((i%2) == 0): direction='x'
   else           : direction='y'
   number=int(i/2)+1

   # Create axes if they don't already exist; linear autoscaling axes
   if (not number in axes_this[direction]): axes_this[direction][number] = {'SETTINGS':gp_settings.default_new_axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

   if 'min'     in command['range_list'][i]: axes_this[direction][number]['SETTINGS']['MIN'] = command['range_list'][i]['min']
   if 'max'     in command['range_list'][i]: axes_this[direction][number]['SETTINGS']['MAX'] = command['range_list'][i]['max']
   if 'minauto' in command['range_list'][i]: axes_this[direction][number]['SETTINGS']['MIN'] = None
   if 'maxauto' in command['range_list'][i]: axes_this[direction][number]['SETTINGS']['MAX'] = None

  # We leave the setting up of the key until a later date
  key = None

  # Add list of things to plot to plotlist (we use extend, as replot keeps the old list)
  if 'plot_list,' in command: plotlist.extend(command['plot_list,'])

  # Add plot to multiplot list (we do this even when not in multiplot mode, in which case the list has just been wiped, and will only have one member)
  this_plotdesc = {'itemtype':'plot',
                   'number'  :replot_focus, # This is filled in below if replot_focus is None
                   'plotlist':plotlist,
                   'key'     :key,
                   'settings':settings.copy(),
                   'labels'  :labels.copy(),
                   'arrows'  :arrows.copy(),
                   'deleted' :'OFF',
                   'axes'    :None, # Fill in this below
                   'listdesc':commandtext
                   }

  for item in this_plotdesc['plotlist']: # Turn string variables into filenames
    if ('expression_list:' in item):
     if len(item['expression_list:'])==1:
      filename_var = item['expression_list:'][0]['expression'].strip()
      if (filename_var in vars):
       if (type(vars[filename_var])==type("")):
        item['filename']=vars[filename_var]
        del item['expression_list:']

  if (replot_stat != 0) and (replot_focus != None): # If replotting a multiplot, overwrite last graph
   multiplot_plotdesc[replot_focus] = this_plotdesc
  else:
   replot_stat = 0 # We're not replotting, as there's nothing to replot
   multiplot_plotdesc.append( this_plotdesc )
   replot_focus = len(multiplot_plotdesc)-1
   multiplot_plotdesc[replot_focus]['number'] = replot_focus
  multiplot_plotdesc[replot_focus]['settings']['ORIGINX'] = x_position # Reset origin, bearing in mind that we may be replotting something which had been moved
  multiplot_plotdesc[replot_focus]['settings']['ORIGINY'] = y_position

  # Make a copy of axes_this and add it to multiplot catalogue of graph axes
  # We do a copy here, because 'set xlabel' will modify axes_this, in case we want to do a replot
  # But we don't want it to poke around with our latest multiplot addition (unless we replot that).
  axes_this_cpy = { 'x':{},'y':{},'z':{} }
  for [direction,axis_list_to] in axes_this_cpy.iteritems():
   for [number,axis] in axes_this[direction].iteritems():
    axis_list_to[number] = {'SETTINGS':axis['SETTINGS'].copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}
  multiplot_plotdesc[replot_focus]['axes'] = axes_this_cpy

  # Go ahead and make a canvas and plot everything!
  if interactive and (gp_settings.settings_global['MULTIPLOT'] == 'ON') and ((replot_stat == 0) or (replot_focus == None)):
   gp_report("Plot added to multiplot with reference %d."%this_plotdesc['number'])

  if (gp_settings.settings_global['DISPLAY'] == "ON"):
   try:
    unsuccessful_plot_operations = gp_plot.multiplot_plot(linestyles,vars,settings,multiplot_plotdesc)
   except KeyboardInterrupt: raise
   except:
    gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return

   if (gp_settings.settings_global['MULTIPLOT'] == 'ON') and (replot_stat == 0) and (this_plotdesc['number'] in unsuccessful_plot_operations) and (gp_settings.settings_global['DISPLAY'] == "ON"):
    multiplot_plotdesc.pop()
    if interactive:
     gp_report("Plot has been removed from multiplot, because it generated an error.")
