# PYXPLOT.PY
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

exitting = 0

import gp_children
import gp_settings
import gp_eval
import gp_userspace
import gp_fit
import gp_canvas
import gp_postscript
import gp_text
import gp_help
import gp_version
import gp_spline
import gp_histogram
import gp_tabulate
from gp_autocomplete import *
import gp_parser
import gp_error
from gp_error import *
import gp_plot

import os
import sys
import glob
import signal
from math import *
import re

try: import readline
except: READLINE_ABSENT= True
else: READLINE_ABSENT = False

try: import scipy
except: SCIPY_ABSENT = True
else: SCIPY_ABSENT = False

# WITH_WORDS_PRINT(): Convert a dictionary of with words into a user-readable string
def with_words_print(definition, include_with=False):
  outstring = ""
  if 'style'          in definition: outstring += "%s "%definition['style']
  if 'colour'         in definition: outstring += "colour %s "%definition['colour']
  if 'fillcolour'     in definition: outstring += "fillcolour %s "%definition['fillcolour']
  if 'linestyle'      in definition: outstring += "linestyle %d "%definition['linestyle']
  if 'linetype'       in definition: outstring += "linetype %d "%definition['linetype']
  if 'linewidth'      in definition: outstring += "linewidth %s "%definition['linewidth']
  if 'pointlinewidth' in definition: outstring += "pointlinewidth %s "%definition['pointlinewidth']
  if 'pointsize'      in definition: outstring += "pointsize %d "%definition['pointsize']
  if 'pointtype'      in definition: outstring += "pointtype %d "%definition['pointtype']
  if include_with and (outstring != ""): outstring = "with "+outstring
  return outstring

# ACCESS_AXIS(): Returns axis settings for an axis. If axis doesn't exist, then
# create it.

def access_axis(axisname):
 if (axisname == None): # None means we return a list of all axes
  output = []
  for axis_dir in gp_settings.axes.keys():
   for axis_n in gp_settings.axes[axis_dir].keys():
    output.append( [ axis_dir, axis_n, gp_settings.axes[axis_dir][axis_n], False ] )
  for axis_dir in gp_canvas.axes_this.keys():
   for axis_n in gp_canvas.axes_this[axis_dir].keys():
    output.append( [ axis_dir, axis_n, gp_canvas.axes_this[axis_dir][axis_n]['SETTINGS'], False ] )
  output.append( [ 'd', 0, gp_settings.default_new_axis, False ] ) # Also modify the default new axis
  return output
 else:
  axis_dir = axisname[0]
  if (len(axisname) == 1): axis_n = 1 # "x" means axis "x1"
  else                   : axis_n = int(axisname[1:])

  if axis_n not in gp_settings.axes[axis_dir]: # Create axis if it doesn't already exist
   gp_settings.axes[axis_dir][axis_n] = gp_settings.default_new_axis.copy()

  return [ [ axis_dir, axis_n, gp_settings.axes[axis_dir][axis_n], True ] ]

# COPY_AXIS_INFO_TO_GPPLOT(): This is called at the end of commands such as
# "set xtics". Having set axis settings in gp_settings, we also make any
# necessary changes in gp_canvas.axes_this to ensure that the replot command does
# the right thing. This is necessary because the user may have set ranges on
# axes in the plot command, which gp_canvas needs to remember.

def copy_axis_info_to_gpplot(axisname, attributes):
 assert axisname != None
 [direction, number, axis_in, commit] = access_axis(axisname)[0]
 assert commit == True

 if (not number in gp_canvas.axes_this[direction]):
  gp_canvas.axes_this[direction][number] = {'SETTINGS':axis_in.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None} # Create axis if doesn't exist
 else:
  for attribute in attributes:
   gp_canvas.axes_this[direction][number]['SETTINGS'][attribute] = axis_in[attribute]

# Directive Show

def directive_show(dictlist):
  if (len(dictlist) == 0):
    gp_error(gp_text.show)
  else:
    for dict in dictlist:
      word = dict['setting']
      if autocomplete(word, "all",1):
        directive_show([{'setting':"settings"},
                        {'setting':"axes_"},
                        {'setting':"linestyles"},
                        {'setting':"variables"},
                        {'setting':"functions"}])
        continue
      outstring = ""
      if autocomplete(word, "settings", 1) or autocomplete(word, "axescolour",1): outstring += "Axes colour:   %s\n"%gp_settings.settings['AXESCOLOUR']
      if autocomplete(word, "settings", 1) or autocomplete(word, "backup", 1):    outstring += "File backups:  %s\n"%gp_settings.settings_global['BACKUP']
      if autocomplete(word, "settings", 1) or autocomplete(word, "bar",1):        outstring += "Bar width:     %f (the size of the strokes at the end of errorbars, set with 'set bar')\n"%gp_settings.settings['BAR']
      if autocomplete(word, "settings", 1) or autocomplete(word, "binorigin",1):  outstring += "Bin origin:    %f (the x-origin of a histogram bin)\n"%gp_settings.settings['BINORIGIN']
      if autocomplete(word, "settings", 1) or autocomplete(word, "binwidth",1):   outstring += "Bin width:     %f (the width of a histogram bin)\n"%gp_settings.settings['BINWIDTH']
      if autocomplete(word, "settings", 1) or autocomplete(word, "boxwidth",1):   outstring += "Boxwidth:      %s (the default width of bars on barcharts and histograms; a negative value means automatic widths)\n"%gp_settings.settings['BOXWIDTH']
      if autocomplete(word, "settings", 1) or autocomplete(word, "boxfrom",1):    outstring += "BoxFrom:       %s (the vertical point from which the bars of barcharts and histograms emanate)\n"%gp_settings.settings['BOXFROM']
      if autocomplete(word, "settings", 1) or autocomplete(word, "display", 1)  : outstring += "Display:       %s\n"%gp_settings.settings_global['DISPLAY']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
                                                   autocomplete(word, "dpi", 1)): outstring += "Output DPI:    %f (only relevant when output is sent to a bitmap terminal -- gif, jpg or png)\n"%gp_settings.settings_global['DPI']
      if autocomplete(word, "settings", 1) or autocomplete(word, "fontsize",1) or autocomplete(word, "fountsize",1):   outstring += "Fontsize:      %d (-4 is smallest, 5 largest)\n"%gp_settings.settings['FONTSIZE']
      if autocomplete(word, "settings", 1) or autocomplete(word, "grid",1):
        outstring += "Grid:          %s\n"%gp_settings.settings['GRID']
        if (gp_settings.settings['GRID'] == 'ON'):
          outstring += "Grid Axes:     "
          for axis_n in gp_settings.settings['GRIDAXISX']: outstring += "x%d "%axis_n
          for axis_n in gp_settings.settings['GRIDAXISY']: outstring += "y%d "%axis_n
          outstring += "\n"
      if autocomplete(word, "settings", 1) or autocomplete(word, "gridmajcolour",1): outstring += "Grid major col:%s\n"%gp_settings.settings['GRIDMAJCOLOUR']
      if autocomplete(word, "settings", 1) or autocomplete(word, "gridmincolour",1): outstring += "Grid minor col:%s\n"%gp_settings.settings['GRIDMINCOLOUR']
      if autocomplete(word, "settings", 1) or autocomplete(word, "key",1):        outstring += "Key:           %s (selects whether a legend appears on plots)\n"%gp_settings.settings['KEY']
      if autocomplete(word, "settings", 1) or autocomplete(word, "keycolumns",1): outstring += "Key columns:   %s\n"%gp_settings.settings['KEYCOLUMNS']
      if autocomplete(word, "settings", 1) or autocomplete(word, "key",1):        outstring += "Key position:  %s, with offset (%f,%f)\n"%(gp_settings.settings['KEYPOS'],gp_settings.settings['KEY_XOFF'],gp_settings.settings['KEY_YOFF'])
      if(autocomplete(word, "settings", 1) or autocomplete(word, "linewidth", 1) or
                                              autocomplete(word, "lw",2)       ): outstring += "Linewidth:     %f\n"%gp_settings.settings['LINEWIDTH']
      if autocomplete(word, "settings", 1) or autocomplete(word, "multiplot", 1): outstring += "Multiplot:     %s\n"%gp_settings.settings_global['MULTIPLOT']
      if autocomplete(word, "settings", 1) or autocomplete(word, "origin", 1):    outstring += "Plot Offset:  (%f,%f)\n"%(gp_settings.settings['ORIGINX'],gp_settings.settings['ORIGINY'])
      if autocomplete(word, "settings", 1) or autocomplete(word, "output", 1):    outstring += "Output fname:  %s\n"%gp_settings.settings_global['OUTPUT']
      if autocomplete(word, "settings", 1) or autocomplete(word, "palette",1):    outstring += "Palette:       %s\n"%gp_settings.colour_list
      if autocomplete(word, "settings", 1) or autocomplete(word, "papersize", 1): outstring += "Papersize:     %s (%s by %s mm)\n"%(gp_settings.settings_global['PAPER_NAME'],gp_settings.settings_global['PAPER_HEIGHT'],gp_settings.settings_global['PAPER_WIDTH'])
      if (autocomplete(word, "settings", 1) or
          autocomplete(word, "pointlinewidth",1) or autocomplete(word, "plw",3)): outstring += "Pointlinewidth:%f\n"%gp_settings.settings['POINTLINEWIDTH']
      if(autocomplete(word, "settings", 1) or autocomplete(word, "pointsize", 1) or
                                              autocomplete(word, "ps",2)       ): outstring += "Pointsize:     %f\n"%gp_settings.settings['POINTSIZE']
      if autocomplete(word, "settings", 1) or autocomplete(word, "preamble", 1):  outstring += "LaTeX preamble:%s\n"%gp_settings.latex_preamble
      if autocomplete(word, "settings", 1) or autocomplete(word, "samples",1):    outstring += "Samples        %d (no of samples used when plotting functions)\n"%gp_settings.settings['SAMPLES']
      if autocomplete(word, "settings", 1) or autocomplete(word, "size", 1):
       if (gp_settings.settings['AUTOASPECT'] == "ON"): outstring += "Output aspect: <auto>\n"
       else                                           : outstring += "Output aspect: %f\n"%gp_settings.settings['ASPECT']
      if(autocomplete(word, "settings", 1) or autocomplete(word, "data", 1) or
                                               autocomplete(word, "style",1)):    outstring += "Data style:    %s (the default plotting style for datafiles, if none is specified)\n"%with_words_print(gp_settings.settings['DATASTYLE'],False)
      if(autocomplete(word, "settings", 1) or autocomplete(word, "function", 1) or
                                               autocomplete(word, "style",1)):    outstring += "Function style:%s (the default plotting style for functions, if none is specified)\n"%with_words_print(gp_settings.settings['FUNCSTYLE'],False)
      if autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1):  outstring += "Terminal type: %s\n"%gp_settings.settings_global['TERMTYPE']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
                                               autocomplete(word, "antialias",1)):outstring += "Anti-Aliasing: %s\n"%gp_settings.settings_global['TERMANTIALIAS']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
                                               autocomplete(word, "colour",1)):   outstring += "Colour:        %s (when off, all plots will be monochrome)\n"%gp_settings.settings_global['COLOUR']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
                                               autocomplete(word, "enlarge",1)):  outstring += "Enlarge:       %s (when on, output is enlarged to paper size)\n"%gp_settings.settings_global['TERMENLARGE']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
                                               autocomplete(word, "invert",1)):   outstring += "Invert colours:%s (only relevant when output is sent to a bitmap terminal -- gif, jpg or png)\n"%gp_settings.settings_global['TERMINVERT']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
         autocomplete(word, "landscape", 1) or autocomplete(word, "portrait", 1)):outstring += "Landscape mode:%s\n"%gp_settings.settings_global['LANDSCAPE']
      if (autocomplete(word, "settings", 1) or autocomplete(word, "terminal", 1) or
         autocomplete(word, "transparent", 1) or autocomplete(word, "solid", 1)): outstring += "Transparency:  %s (only relevant when output is sent to gif or png terminals, which support transparency)\n"%gp_settings.settings_global['TERMTRANSPARENT']
      if autocomplete(word, "settings", 1) or autocomplete(word, "textcolour",1): outstring += "Text colour:   %s\n"%gp_settings.settings['TEXTCOLOUR']
      if autocomplete(word, "settings", 1) or autocomplete(word, "texthalign",1): outstring += "Text halign:   %s\n"%gp_settings.settings['TEXTHALIGN']
      if autocomplete(word, "settings", 1) or autocomplete(word, "textvalign",1): outstring += "Text valign:   %s\n"%gp_settings.settings['TEXTVALIGN']
      if autocomplete(word, "settings", 1) or autocomplete(word, "title", 1):     outstring += "Plot Title:   '%s' at offset (%f,%f)\n"%(gp_settings.settings['TITLE'],gp_settings.settings['TIT_XOFF'],gp_settings.settings['TIT_YOFF'])
      if(autocomplete(word, "settings", 1) or autocomplete(word, "width", 1) or
                                               autocomplete(word, "size", 1)):    outstring += "Output width:  %s\n"%gp_settings.settings['WIDTH']

      if autocomplete(word, "linestyles", 1) or (word=="ls"):
       outstring += "\nLinestyles:\n"
       for i,definition in gp_settings.linestyles.iteritems(): outstring += "  linestyle %d: %s\n"%(i,with_words_print(definition,False))

      if autocomplete(word, "arrows",1):
        outstring += "\nArrows:\n"
        for i,definition in gp_settings.arrows.iteritems():
          outstring += "  arrow %d: (%s %s,%s %s) to (%s %s,%s %s) %s\n"%(i, definition[0], definition[1], definition[2], definition[3], definition[4], definition[5], definition[6], definition[7], with_words_print(definition[8],True))

      if autocomplete(word, "labels",1):
        outstring += "\nText labels:\n"
        for i,definition in gp_settings.labels.iteritems():
          outstring += "  label %d: %s at (%s %s,%s %s), rotation angle %s\n"%(i, definition[0], definition[1], definition[2], definition[3], definition[4], definition[5])

      for [direction , direction_axes] in gp_settings.axes.iteritems():
       for [axis_number, axis] in direction_axes.iteritems():
        axisoutstring = ""
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "%s%dlabel"%(direction,axis_number),1) or ((axis_number==1)and(autocomplete(word, "%slabel"%direction,1))):
          axisoutstring += "  Label:     %s\n"%axis['LABEL']
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "%s%drange"%(direction,axis_number),1) or ((axis_number==1)and(autocomplete(word, "%srange"%direction,1))) or autocomplete(word, "autoscale",1):
          if (axis['MIN'] == None): mintxt = "<auto>"
          else                    : mintxt = axis['MIN']
          if (axis['MAX'] == None): maxtxt = "<auto>"
          else                    : maxtxt = axis['MAX']
          axisoutstring += "  Range:    (%s --> %s)\n"%(mintxt,maxtxt)
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "logscale",1):
          axisoutstring += "  Log:       %s"%axis['LOG']
          if (axis['LOG'] == "ON"): axisoutstring += " (base %d)\n"%axis['LOGBASE']
          else                    : axisoutstring += " (display scientific exponentials to base %d)\n"%axis['LOGBASE']
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "%s%dtics"%(direction,axis_number),1) or ((axis_number==1)and(autocomplete(word, "%stics"%direction,1))):
          axisoutstring += "  Ticks:     "
          if   (axis['TICKLIST'] != None):
           axisoutstring += "\n"
           for tick in axis['TICKLIST']:
            axisoutstring += "    %16s %s\n"%(tick[0],tick[1])
          elif (axis['TICKSTEP'] != None):
           if   (axis['TICKMIN'] == None): axisoutstring += "from axis minimum, with separation %s.\n"%axis['TICKSTEP']
           elif (axis['TICKMAX']   == None): axisoutstring += "from %s, with separation %s.\n"%(axis['TICKMIN'],axis['TICKSTEP'])
           else                            : axisoutstring += "from %s, with separation %s, to %s.\n"%(axis['TICKMIN'],axis['TICKSTEP'],axis['TICKMAX'])
          else:
           axisoutstring += "automatic\n"
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "m%s%dtics"%(direction,axis_number),1) or ((axis_number==1)and(autocomplete(word, "m%stics"%direction,1))):
          axisoutstring += "  Minor Tics:"
          if   (axis['MTICKLIST'] != None):
           axisoutstring += "\n"
           for tick in axis['MTICKLIST']:
            axisoutstring += "    %16s %s\n"%(tick[0],tick[1])
          elif (axis['MTICKSTEP'] != None):
           if   (axis['MTICKMIN'] == None): axisoutstring += "from axis minimum, with separation %s.\n"%axis['MTICKSTEP']
           elif (axis['MTICKMAX']   == None): axisoutstring += "from %s, with separation %s.\n"%(axis['MTICKMIN'],axis['MTICKSTEP'])
           else                            : axisoutstring += "from %s, with separation %s, to %s.\n"%(axis['MTICKMIN'],axis['MTICKSTEP'],axis['MTICKMAX'])
          else:
           axisoutstring += "automatic\n"
        if autocomplete(word, "axes_",1) or autocomplete(word, "axis",1) or autocomplete(word, "%s%dticdir"%(direction,axis_number),1) or ((axis_number==1)and(autocomplete(word, "%sticdir"%direction,1))):
          axisoutstring += "  Tick Direction: %s\n"%axis['TICDIR']
        if (len(axisoutstring) > 0): outstring += "\nSettings for %s%s axis:\n"%(direction,axis_number)+axisoutstring

      if autocomplete(word, "variables",1) or (word=="vars"):
        outstring += "\nVariables:\n"
        for x,y in gp_userspace.variables.iteritems():
          outstring += "%s = %s\n"%(x,y)
        outstring += "\n"

      if autocomplete(word, "functions",1) or (word=="funcs"):
        outstring += "\nUser-Defined Functions:\n"
        for x,y in gp_userspace.functions.iteritems():
         if (y['type']=='spline'): # This is a spline
           outstring += x + "(x) = spline fit to file %s.\n"%y['fname']
         elif (y['histogram']):    # This is a histogram function
           outstring += x + "(x) = histogram of data in file %s.\n"%y['fname']
         else: # This is a regular function
          for definition in y['defn']:
           string = x+"("
           ranges = " for "
           for i in range(y['no_args']):
            if (i != 0): string += ","
            string += definition['args'][i]
            if   (i != 0) and (i != y['no_args']-1): ranges += ", "
            elif (i != 0) and (i == y['no_args']-1): ranges += " and "
            if (definition['ranges'][i] == [None,None]): ranges += "all "+definition['args'][i]
            else:
             ranges += "("
             if (definition['ranges'][i][0] == None): ranges += "-inf"
             else                                   : ranges += definition['ranges'][i][0]
             ranges += " < "+definition['args'][i]+" < "
             if (definition['ranges'][i][1] == None): ranges += "inf"
             else                                   : ranges += definition['ranges'][i][1]
             ranges += ")"
           outstring += string+") = "+definition['expr']+"\n"
           outstring += ranges+"\n"

      if (len(outstring) == 0):
        if   re.match(r"(x|y|z|X|Y|Z)\d\d*(L|l)((A|a)((B|b)((E|e)((L|l)?)?)?)?)?$",word) != None: gp_error("Error: show command requested to show label on non-existent axis '%s'."%word)
        elif re.match(r"(x|y|z|X|Y|Z)\d\d*(R|r)((A|a)((N|n)((G|g)((E|e)?)?)?)?)?$",word) != None: gp_error("Error: show command requested to show range of non-existent axis '%s'."%word)
        elif re.match(r"(x|y|z|X|Y|Z)\d\d*(T|t)((I|i)((C|c)((D|d)((I|i)((R|r)?)?)?)?)?)?$",word) != None: gp_error("Error: show command requested to show ticdir of non-existent axis '%s'."%word)
        else:
          gp_error("Error: show command passed unrecognised word '%s'."%word)
          gp_error(gp_text.show)
      else:
        gp_report(outstring)
  return

# Directive Set / Unset

def directive_set_unset(userinput):

  if   (userinput['directive'] == "set") and (userinput['set_option'] == "arrow"): # set arrow
     state = True
     for key in ['x1_system','y1_system','x2_system','y2_system']:
      if key not in userinput: userinput[key] = 'first'
      try:
       x = int(userinput[key])
       if (x<1):
        gp_error("set arrow command refers to axis %s%d; negative axes are not allowed."%(key[0],x))
        state=False
       else: userinput[key]="axis%d"%x
      except KeyboardInterrupt: raise
      except: pass
     if state:
      arrow_id = userinput['arrow_id']
      x1s      = userinput['x1_system']
      y1s      = userinput['y1_system']
      x2s      = userinput['x2_system']
      y2s      = userinput['y2_system']
      x1p      = userinput['x1']
      y1p      = userinput['y1']
      x2p      = userinput['x2']
      y2p      = userinput['y2']
      gp_settings.arrows[arrow_id] = (x1s,x1p,y1s,y1p,x2s,x2p,y2s,y2p,userinput)

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "arrow"): # unset arrow
     if userinput['arrow_list,'] == []:
      gp_settings.arrows = {} # unset arrow alone wipes all arrows
     else:
      for aid_dict in userinput['arrow_list,']:
       arrow_id = aid_dict['arrow_id']
       if arrow_id in gp_settings.arrows:
        del gp_settings.arrows[arrow_id] # Delete key from arrow dictionary
       else:
        gp_error("Error removing arrow %d -- no such arrow."%arrow_id)


  elif (userinput['set_option'] == 'autoscale'): # set autoscale | unset autoscale
     for axis_dict in userinput['axes']:
      axisname = axis_dict['axis']
      [direction,number,axis,commit] = access_axis(axisname)[0]
      axis["MIN"] = axis["MAX"] = None
      if commit: copy_axis_info_to_gpplot(axisname, ["MIN","MAX"])

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "axis"): # set axis
      for axis_dict in userinput['axes']:
       direction = axis_dict['axis'][0]
       axis_n = int(axis_dict['axis'][1:])
       if (not axis_n in gp_settings.axes[direction]):
        gp_settings.axes[direction][axis_n] = gp_settings.default_new_axis.copy()
        gp_canvas.axes_this[direction][axis_n] = {'SETTINGS':gp_settings.axes[direction][axis_n].copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "axis"): # unset axis
      for axis_dict in userinput['axes']:
       direction = axis_dict['axis'][0]
       axis_n = int(axis_dict['axis'][1:])
       if (axis_n in gp_settings.axes[direction]):
        del gp_settings.axes[direction][axis_n]
       else:
        gp_warning("Warning: attempt to unset axis %s; no such axis."%(axis_dict['axis']))
       if (axis_n in gp_canvas.axes_this[direction]): del gp_canvas.axes_this[direction][axis_n]
       if (axis_n == 1):
        gp_settings.axes[direction][1]  = gp_settings.default_new_axis.copy()
        gp_canvas.axes_this[direction][1] = {'SETTINGS':gp_settings.axes[direction][axis_n].copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}


  elif (userinput['directive'] == "set") and (userinput['set_option'] == "backup"): # set backup
     gp_settings.settings_global['BACKUP'] = "ON"

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "backup"): # unset backup
     gp_settings.settings_global['BACKUP'] = gp_settings.settings_global_default['BACKUP']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "bar"): # set bar
     gp_settings.settings['BAR'] = float(userinput['bar_size'])

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "bar"): # unset bar
     gp_settings.settings['BAR'] = gp_settings.settings_default['BAR']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "binorigin"): # set bar
     gp_settings.settings['BINORIGIN'] = float(userinput['bin_origin'])

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "binorigin"): # unset bar
     gp_settings.settings['BINORIGIN'] = gp_settings.settings_default['BINORIGIN']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "binwidth"): # set bar
     gp_settings.settings['BINWIDTH'] = float(userinput['bin_width'])

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "binwidth"): # unset bar
     gp_settings.settings['BINWIDTH'] = gp_settings.settings_default['BINWIDTH']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "boxfrom"): # set boxfrom
     gp_settings.settings['BOXFROM'] = userinput['box_from']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "boxfrom"): # unset boxfrom
     gp_settings.settings['BOXFROM'] = gp_settings.settings_default['BOXFROM']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "boxwidth"): # set boxwidth
     gp_settings.settings['BOXWIDTH'] = userinput['box_width']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "boxwidth"): # unset boxwidth
     gp_settings.settings['BOXWIDTH'] = gp_settings.settings_default['BOXWIDTH']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "display"): # set display
     gp_settings.settings_global['DISPLAY'] = 'ON'

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "display"): # unset display
     gp_settings.settings_global['DISPLAY'] = gp_settings.settings_global_default['DISPLAY']
     
  elif (userinput['directive'] == "set") and (userinput['set_option'] == "dpi"): # set dpi
     if (userinput['dpi'] < 2.0):
      gp_error("Error: the set dpi command should be followed by a positive value >= 2.")
     else:
      gp_settings.settings_global['DPI'] = userinput['dpi']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "dpi"): # unset dpi
     gp_settings.settings_global['DPI'] = gp_settings.settings_global_default['DPI']
     
  elif (userinput['directive'] == "set") and (userinput['set_option'] == "fontsize"): # set fontsize
     if (userinput['fontsize'] < -4): userinput['fontsize'] = -4
     if (userinput['fontsize'] >  5): userinput['fontsize'] =  5
     gp_settings.settings['FONTSIZE'] = userinput['fontsize']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "fontsize"): # unset fontsize
     gp_settings.settings['FONTSIZE'] = gp_settings.settings_default['FONTSIZE']

  elif (userinput['set_option'] in ['axescolour','gridmajcolour','gridmincolour','textcolour']): # set axescolour | set gridmajcolour | set gridmincolour
     set_opt = userinput['set_option'].upper()                                                   # set textcolour
     if (userinput['directive'] == "unset"):
      gp_settings.settings[set_opt] = gp_settings.settings_default[set_opt]
     else:
      if (userinput['colour'].capitalize() in gp_settings.colours):
       gp_settings.settings[set_opt] = userinput['colour'].capitalize()
      else:
       try:
        colnum = gp_eval.gp_eval(userinput['colour'], gp_userspace.variables, verbose=False)
        gp_settings.settings[set_opt] = gp_settings.colour_list[(int(colnum)-1)%len(gp_settings.colour_list)]
       except KeyboardInterrupt: raise
       except:
        gp_error("Expression '%s' was not recognised as a colour name, nor does it compute as a colour number:"%userinput['colour'])
        try:
         dummy = gp_eval.gp_eval(userinput['colour'], gp_userspace.variables, verbose=True)
        except KeyboardInterrupt: raise
        except: pass

  elif (userinput['directive'] == "set") and (userinput['set_option'] == 'grid'): # set grid
     if (gp_settings.settings['GRID'] != 'ON'): gp_settings.settings['GRID']='ON'

     if userinput['axes']==[]:
      gp_settings.settings['GRIDAXISX']=gp_settings.settings_default['GRIDAXISX'][:] # set grid alone puts grid onto default axes
      gp_settings.settings['GRIDAXISY']=gp_settings.settings_default['GRIDAXISY'][:]
     else:
      xl=gp_settings.settings['GRIDAXISX']=[] # set grid <axis> puts a grid only onto specified axis
      yl=gp_settings.settings['GRIDAXISY']=[]
      for axis_dict in userinput['axes']:
       axisname = axis_dict['axis']
       direction = axisname[0]
       number    = int(axisname[1:])
       if (direction == 'x') and (number not in xl): xl.append(number)
       if (direction == 'y') and (number not in yl): yl.append(number)

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == 'grid'): # unset grid
     gp_settings.settings['GRID']      = gp_settings.settings_default['GRID']
     gp_settings.settings['GRIDAXISX'] = gp_settings.settings_default['GRIDAXISX'][:] # set grid alone puts grid onto default axes
     gp_settings.settings['GRIDAXISY'] = gp_settings.settings_default['GRIDAXISY'][:]

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "key"): # set key
     gp_settings.settings['KEY'] = 'ON'
     if 'pos' in userinput:
      if (userinput['pos'] == 'below'  ): gp_settings.settings['KEYPOS'] = "BELOW"
      if (userinput['pos'] == 'above'  ): gp_settings.settings['KEYPOS'] = "ABOVE"
      if (userinput['pos'] == 'outside'): gp_settings.settings['KEYPOS'] = "OUTSIDE"
     if 'xpos' in userinput:
      if (len(gp_settings.settings['KEYPOS'].split()) != 2): gp_settings.settings['KEYPOS'] = "TOP RIGHT" # Deal with if previously "below"
      if (userinput['xpos'] == 'left'   ): gp_settings.settings['KEYPOS'] = gp_settings.settings['KEYPOS'].split()[0] + ' LEFT'
      if (userinput['xpos'] == 'right'  ): gp_settings.settings['KEYPOS'] = gp_settings.settings['KEYPOS'].split()[0] + ' RIGHT'
      if (userinput['xpos'] == 'xcentre'): gp_settings.settings['KEYPOS'] = gp_settings.settings['KEYPOS'].split()[0] + ' MIDDLE'
     if 'ypos' in userinput:
      if (len(gp_settings.settings['KEYPOS'].split()) != 2): gp_settings.settings['KEYPOS'] = "TOP RIGHT" # Deal with if previously "below"
      if (userinput['ypos'] == 'top'    ): gp_settings.settings['KEYPOS'] = 'TOP '    + gp_settings.settings['KEYPOS'].split()[1]
      if (userinput['ypos'] == 'bottom' ): gp_settings.settings['KEYPOS'] = 'BOTTOM ' + gp_settings.settings['KEYPOS'].split()[1]
      if (userinput['ypos'] == 'ycentre'): gp_settings.settings['KEYPOS'] = 'MIDDLE ' + gp_settings.settings['KEYPOS'].split()[1]
     if 'x_offset' in userinput: gp_settings.settings['KEY_XOFF'] = userinput['x_offset']
     else                      : gp_settings.settings['KEY_XOFF'] = 0.0
     if 'y_offset' in userinput: gp_settings.settings['KEY_YOFF'] = userinput['y_offset']
     else                      : gp_settings.settings['KEY_YOFF'] = 0.0

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "key"): # unset key
     for X in ['KEY','KEYPOS','KEY_XOFF','KEY_YOFF']: gp_settings.settings[X] = gp_settings.settings_default[X]

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "keycolumns"): # set keycolumns
     gp_settings.settings['KEYCOLUMNS'] = userinput['key_columns']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "keycolumns"): # unset keycolumns
     gp_settings.settings['KEYCOLUMNS'] = gp_settings.settings_default['KEYCOLUMNS']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "label"): # set label
     if 'x_system' not in userinput: userinput['x_system'] = 'first'
     if 'y_system' not in userinput: userinput['y_system'] = 'first'
     if 'rotation' not in userinput: userinput['rotation'] = 0.0
     state=True
     for dir in "xy":
      try:
       x = int(userinput['%s_system'%dir])
       if (x<1):
        gp_error("set label command refers to axis %s%d; negative axes are not allowed."%(dir,x))
        state=False
       else: userinput['%s_system'%dir]="axis%d"%x
      except KeyboardInterrupt: raise
      except: pass

     if state:
      label_id = userinput['label_id']
      text     = userinput['label_text']
      xp       = userinput['x_position']
      yp       = userinput['y_position']
      xs       = userinput['x_system']
      ys       = userinput['y_system']
      rot      = userinput['rotation']
      if 'colour' not in userinput: userinput['colour'] = gp_settings.settings['TEXTCOLOUR']
      texthal  = gp_settings.settings['TEXTHALIGN']
      textval  = gp_settings.settings['TEXTVALIGN']
      textsize = gp_settings.settings['FONTSIZE']
      gp_settings.labels[label_id] = (text,xs,xp,ys,yp,rot,userinput['colour'],texthal,textval,textsize)

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "linestyle"): # set linestyle
     gp_settings.linestyles[userinput['linestyle_id']] = userinput

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "linestyle"): # unset linestyle
     if userinput['linestyle_ids,'] == []:
       gp_settings.linestyles = {}
     else:
       for ls_dict in userinput['linestyle_ids,']:
        if ls_dict['id'] in gp_settings.linestyles:
         del gp_settings.linestyles[ls_dict['id']]
        else:
         gp_error("Error removing linestyle %d -- no such linestyle."%ls_dict['id'])

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "linewidth"): # set linewidth
     gp_settings.settings['LINEWIDTH'] = userinput['linewidth']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "linewidth"): # unset linewidth
     gp_settings.settings['LINEWIDTH'] = gp_settings.settings_default['LINEWIDTH']

  elif (userinput['set_option'] == 'logscale'):         # set logscale
     if 'base' not in userinput: userinput['base'] = 10 # default use base 10
     if (userinput['base'] < 2) or (userinput['base'] > 1024):
      gp_warning("Warning: Attempt to use log axis with base %d. PyXPlot only supports bases in the range 2 - 1024. Defaulting to base 10."%userinput['base'])
      userinput['base'] = 10
     for axis_dict in userinput['axes']:
      axisname = axis_dict['axis']
      [direction,number,axis,commit] = access_axis(axisname)[0]
      axis["LOG"]     = "ON"
      axis["LOGBASE"] = userinput['base']
      if commit: copy_axis_info_to_gpplot(axisname, ["LOG","LOGBASE"])

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "multiplot"): # set multiplot
     if (gp_settings.settings_global['MULTIPLOT'] != "ON"):
      gp_settings.settings_global['MULTIPLOT'] = 'ON'
      gp_canvas.plotorder_clear()

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "multiplot"): # unset multiplot
     if (gp_settings.settings_global_default['MULTIPLOT'] == "ON"):
      if (gp_settings.settings_global['MULTIPLOT'] != "ON"):
       gp_settings.settings_global['MULTIPLOT'] = 'ON'
       gp_canvas.plotorder_clear()
     else:
      gp_settings.settings_global['MULTIPLOT'] = 'OFF'

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "nobackup"): # set nobackup
     gp_settings.settings_global['BACKUP'] = "OFF"

  elif (userinput['directive'] == "set") and (userinput['set_option'] == 'nodisplay'): # set nodisplay
     gp_settings.settings_global['DISPLAY'] = 'OFF'

  elif (userinput['directive'] == "set") and (userinput['set_option'] == 'nogrid'): # set nogrid
     if userinput['axes']==[]:
      gp_settings.settings['GRID'] = 'OFF'
     else:
      xl = gp_settings.settings['GRIDAXISX']
      yl = gp_settings.settings['GRIDAXISY']
      for axis_dict in userinput['axes']:
       axisname = axis_dict['axis']
       direction = axisname[0]
       number    = int(axisname[1:])
       if (direction == 'x') and (number in xl): xl.remove(number)
       if (direction == 'y') and (number in yl): yl.remove(number)

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "nokey"): # set nokey
     gp_settings.settings['KEY']='OFF'

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "label"): # set nolabel | unset label
     if userinput['label_list,'] == []:
      gp_settings.labels = {} # unset label alone wipes all arrows
     else:
      for lid_dict in userinput['label_list,']:
       label_id = lid_dict['label_id']
       if label_id in gp_settings.labels:
        del gp_settings.labels[label_id] # Delete key from label dictionary
       else:
        gp_error("Error removing label %d -- no such label."%label_id)

  elif (userinput['directive'] == "set") and (userinput['set_option'] == 'nologscale'): # set nologscale
     if 'base' not in userinput: userinput['base'] = 10 # default use base 10
     if (userinput['base'] < 2) or (userinput['base'] > 1024):
      gp_warning("Warning: Attempt to use log axis with base %d. PyXPlot only supports bases in the range 2 - 1024. Defaulting to base 10."%userinput['base'])
      userinput['base'] = 10
     for axis_dict in userinput['axes']:
      axisname = axis_dict['axis']
      [direction,number,axis,commit] = access_axis(axisname)[0]
      axis["LOG"] = "OFF"
      axis["LOGBASE"] = userinput['base']
      if commit: copy_axis_info_to_gpplot(axisname, ["LOG","LOGBASE"])

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "nomultiplot"): # set nomultiplot
     gp_settings.settings_global['MULTIPLOT'] = 'OFF'

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "notics"): # set notics
     if 'axis' not in userinput: userinput['axis'] = None # act on all axes
     for [direction,number,axis,commit] in access_axis(userinput['axis']):
       axis['MTICKLIST'] = None # We remove minor ticks, even if user only asks for major ticks to be removed...
       axis['MTICKSTEP'] = 0.0
       if 'minor' not in userinput:
         axis['TICKLIST'] = None
         axis['TICKSTEP'] = 0.0
       if commit: copy_axis_info_to_gpplot(userinput['axis'], ['MTICKLIST','MTICKSTEP','TICKLIST','TICKSTEP'])

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "origin"): # set origin
     gp_settings.settings['ORIGINX'] = userinput['x_origin']
     gp_settings.settings['ORIGINY'] = userinput['y_origin']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "origin"): # unset origin
     gp_settings.settings['ORIGINX'] = gp_settings.settings_default['ORIGINX']
     gp_settings.settings['ORIGINY'] = gp_settings.settings_default['ORIGINY']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "output"): # set output
     gp_settings.settings_global['OUTPUT'] = userinput['filename']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "output"): # unset output
     gp_settings.settings_global['OUTPUT'] = gp_settings.settings_global_default['OUTPUT']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "palette"): # set palette
     palette_new = []
     for coldict in userinput['palette,']:
      colname = coldict['colour'].strip().capitalize()
      if (colname in gp_settings.colours): palette_new.append(colname)
      else                               : gp_error("Error: set palette passed unrecognised colour '%s'; skipping."%coldict['colour'])
     if (len(palette_new) == 0):
      gp_error("Error: set palette command should be followed by a comma-separated list of colours.")
     else:
      gp_settings.colour_list = palette_new

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "palette"): # unset palette
     gp_settings.colour_list = gp_settings.colour_list_default

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "papersize"): # set papersize
     if ('x_size' in userinput):
      h = fabs(userinput['x_size'])
      w = fabs(userinput['y_size'])
      gp_settings.settings_global['PAPER_HEIGHT'] = h
      gp_settings.settings_global['PAPER_WIDTH']  = w
      gp_settings.settings_global['PAPER_NAME']   = gp_postscript.get_papername(h,w)
     else:
      requested = userinput['paper_name'].lower()

      if requested not in gp_postscript.papersizes: # If named papersize is not an exact match, see if it is the beginning of one unique size
       matches = []
       for (name, psize) in gp_postscript.papersizes.iteritems():
        if name[:len(requested)]==requested: matches.append(name) # If requested papersize matches start of papername, add it to list of matches
       if len(matches)==1: requested = matches[0]
 
      if requested in gp_postscript.papersizes:
       [gp_settings.settings_global['PAPER_HEIGHT'], gp_settings.settings_global['PAPER_WIDTH']] = gp_postscript.papersizes[requested]
       gp_settings.settings_global['PAPER_NAME'] = requested
      else:
       gp_error("Error: set papersize passed unrecognised papersize '%s'."%requested)

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "papersize"): # unset papersize
     gp_settings.settings_global['PAPER_HEIGHT'] = gp_settings.settings_global_default['PAPER_HEIGHT']
     gp_settings.settings_global['PAPER_WIDTH']  = gp_settings.settings_global_default['PAPER_WIDTH']
     gp_settings.settings_global['PAPER_NAME']   = gp_settings.settings_global_default['PAPER_NAME']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "pointlinewidth"): # set pointlinewidth
     gp_settings.settings['POINTLINEWIDTH'] = userinput['pointlinewidth']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "pointlinewidth"): # unset pointlinewidth
     gp_settings.settings['POINTLINEWIDTH'] = gp_settings.settings_default['POINTLINEWIDTH']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "pointsize"): # set pointsize
     gp_settings.settings['POINTSIZE'] = userinput['pointsize']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "pointsize"): # unset pointsize
     gp_settings.settings['POINTSIZE'] = gp_settings.settings_default['POINTSIZE']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "preamble"): # set preamble
     gp_settings.latex_preamble = userinput['preamble']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "preamble"): # unset preamble
     gp_settings.latex_preamble = gp_settings.default_latex_preamble

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "samples"): # set samples
     if (userinput['samples'] < 1):
      gp_error("Error: set samples command should be followed by an integer > 1.")
     else:
      gp_settings.settings['SAMPLES'] = userinput['samples']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "samples"): # unset samples
     gp_settings.settings['SAMPLES'] = gp_settings.settings_default['SAMPLES']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "size"): # set size | set width
     if 'width'   in userinput: gp_settings.settings['WIDTH']  = userinput['width']
     if 'ratio'   in userinput: gp_settings.settings['AUTOASPECT'] = 'OFF' ; gp_settings.settings['ASPECT'] = userinput['ratio']
     if 'square'  in userinput: gp_settings.settings['AUTOASPECT'] = 'OFF' ; gp_settings.settings['ASPECT'] = 1.0
     if 'noratio' in userinput: gp_settings.settings['AUTOASPECT'] = 'ON'

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "size"): # unset size
     gp_settings.settings['WIDTH']      = gp_settings.settings_default['WIDTH']
     gp_settings.settings['ASPECT']     = gp_settings.settings_default['ASPECT']
     gp_settings.settings['AUTOASPECT'] = gp_settings.settings_default['AUTOASPECT']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "style"): # set style
     if (userinput['dataset_type'] == "data"): key = "DATASTYLE"
     else                                    : key = "FUNCSTYLE"
     for word in ['style','linetype','linewidth','pointsize','linestyle','pointlinewidth','colour','fillcolour']:
      if word in userinput: gp_settings.settings[key][word] = userinput[word]

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "terminal"): # set terminal
     if 'term'   in userinput: gp_settings.settings_global['TERMTYPE']        = userinput['term']
     if 'antiali'in userinput: gp_settings.settings_global['TERMANTIALIAS']   = userinput['antiali']
     if 'col'    in userinput: gp_settings.settings_global['COLOUR']          = userinput['col']
     if 'enlarge'in userinput: gp_settings.settings_global['TERMENLARGE']     = userinput['enlarge']
     if 'land'   in userinput: gp_settings.settings_global['LANDSCAPE']       = userinput['land']
     if 'trans'  in userinput: gp_settings.settings_global['TERMTRANSPARENT'] = userinput['trans']
     if 'invert' in userinput: gp_settings.settings_global['TERMINVERT']      = userinput['invert']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "terminal"): # unset terminal
     for X in ['TERMTYPE','COLOUR','LANDSCAPE','TERMTRANSPARENT','TERMINVERT','TERMENLARGE']:
      gp_settings.settings_global[X] = gp_settings.settings_global_default[X]

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "texthalign"): # set texthalign
     if 'left'   in userinput: gp_settings.settings['TEXTHALIGN'] = "Left"
     if 'centre' in userinput: gp_settings.settings['TEXTHALIGN'] = "Centre"
     if 'right'  in userinput: gp_settings.settings['TEXTHALIGN'] = "Right"

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "texthalign"): # unset texthalign
     gp_settings.settings['TEXTHALIGN'] = gp_settings.settings_default['TEXTHALIGN']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "textvalign"): # set textvalign
     if 'top'    in userinput: gp_settings.settings['TEXTVALIGN'] = "Top"
     if 'centre' in userinput: gp_settings.settings['TEXTVALIGN'] = "Centre"
     if 'bottom' in userinput: gp_settings.settings['TEXTVALIGN'] = "Bottom"

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "textvalign"): # unset textvalign
     gp_settings.settings['TEXTVALIGN'] = gp_settings.settings_default['TEXTVALIGN']

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "tics"): # set tics
     if 'axis' not in userinput: userinput['axis'] = None # act on all axes
     for [direction,number,axis,commit] in access_axis(userinput['axis']):

       if 'minor' in userinput:
         TICKLIST = 'MTICKLIST' ; TICKMIN ='MTICKMIN' ; TICKSTEP ='MTICKSTEP' ; TICKMAX = 'MTICKMAX'
       else:
         TICKLIST =  'TICKLIST' ; TICKMIN = 'TICKMIN' ; TICKSTEP = 'TICKSTEP' ; TICKMAX =  'TICKMAX'

       if (axis[TICKSTEP] == 0): axis[TICKSTEP] = None # Turn off set noxtics, if this has been done.

       if 'dir' in userinput:
        if (userinput['dir'] == "inward"):  axis['TICDIR'] = "INWARD"
        if (userinput['dir'] == "outward"): axis['TICDIR'] = "OUTWARD"
        if (userinput['dir'] == "both"):    axis['TICDIR'] = "BOTH"

       if 'autofreq' in userinput: # "autofreq" means that we turn off any manually set ticks
        axis[TICKLIST] = None
        axis[TICKMIN]  = None
        axis[TICKSTEP] = None
        axis[TICKMAX]  = None

       if 'tick_list,' in userinput: # User has supplied a list of tick points
        ticklist = []
        axis[TICKLIST] = ticklist
        axis[TICKSTEP] = None
        for tick in userinput['tick_list,']:
         if 'label' not in tick: tick['label'] = None # User hasn't supplied a label; we make one automatically later
         ticklist.append([tick['x'],tick['label']])

       if 'start' in userinput: # User has supplied a start,step,end series for ticks to follow
        axis[TICKLIST] = None
        if not 'increment' in userinput:
         axis[TICKMIN]  = None
         axis[TICKSTEP] = userinput['start']
         axis[TICKMAX]  = None
        else:
         axis[TICKMIN]  = userinput['start']
         axis[TICKSTEP] = userinput['increment']
         if 'end' in userinput:
          axis[TICKMAX] = max(userinput['end'],userinput['start']) # Don't worry if user gives start and end wrong way around
          axis[TICKMIN] = min(userinput['end'],userinput['start'])
         else:
          axis[TICKMAX] = None

       if commit: copy_axis_info_to_gpplot(userinput['axis'], [TICKLIST, TICKMIN, TICKSTEP, TICKMAX, 'TICDIR'] )

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "tics"): # unset tics
     if 'axis' not in userinput: userinput['axis'] = None # act on all axes
     for [direction,number,axis,commit] in access_axis(userinput['axis']):
       if 'minor' in userinput:
         TICKLIST = 'MTICKLIST' ; TICKMIN ='MTICKMIN' ; TICKSTEP ='MTICKSTEP' ; TICKMAX = 'MTICKMAX'
       else:
         TICKLIST =  'TICKLIST' ; TICKMIN = 'TICKMIN' ; TICKSTEP = 'TICKSTEP' ; TICKMAX =  'TICKMAX'
       axis['TICDIR'] = gp_settings.default_axis['TICDIR']
       axis[TICKLIST] = gp_settings.default_axis[TICKLIST]
       axis[TICKMIN]  = gp_settings.default_axis[TICKMIN]
       axis[TICKSTEP] = gp_settings.default_axis[TICKSTEP]
       axis[TICKMAX]  = gp_settings.default_axis[TICKMAX]
       if commit: copy_axis_info_to_gpplot(userinput['axis'], [TICKLIST, TICKMIN, TICKSTEP, TICKMAX, 'TICDIR'] )

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "ticdir"): # set ticdir
     if 'axis' not in userinput: userinput['axis'] = None # act on all axes
     for [direction,number,axis,commit] in access_axis(userinput['axis']):
       axis['TICDIR'] = userinput['dir'].upper()
       if commit: copy_axis_info_to_gpplot(userinput['axis'], ['TICDIR'] )

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "ticdir"): # unset ticdir
     if 'axis' not in userinput: userinput['axis'] = None # act on all axes
     for [direction,number,axis,commit] in access_axis(userinput['axis']):
       axis['TICDIR'] = gp_settings.default_axis['TICDIR']
       if commit: copy_axis_info_to_gpplot(userinput['axis'], ['TICDIR'] )

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "title"): # set title

     gp_settings.settings['TITLE'] = userinput['title']

     if ('x_offset' in userinput): gp_settings.settings['TIT_XOFF'] = userinput['x_offset']
     else                        : gp_settings.settings['TIT_XOFF'] = 0.0

     if ('y_offset' in userinput): gp_settings.settings['TIT_YOFF'] = userinput['y_offset']
     else                        : gp_settings.settings['TIT_YOFF'] = 0.0

  elif ((userinput['directive'] == "set")   and (userinput['set_option'] == "notitle") or
          (userinput['directive'] == "unset") and (userinput['set_option'] == "title"  ) ):

     gp_settings.settings['TITLE']    = gp_settings.settings_default['TITLE']
     gp_settings.settings['TIT_XOFF'] = gp_settings.settings_default['TIT_XOFF']
     gp_settings.settings['TIT_YOFF'] = gp_settings.settings_default['TIT_YOFF']

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "width"): # unset width
     gp_settings.settings['WIDTH'] = gp_settings.settings_default['WIDTH']

  elif (userinput['set_option'] == "xlabel"): # set xlabel / unset xlabel
     if (userinput['directive'] == "unset"): userinput['label_text'] = ""
     [direction,number,axis,commit] = access_axis(userinput['axis'])[0]
     axis['LABEL'] = userinput['label_text'] 
     if commit: copy_axis_info_to_gpplot(userinput['axis'], ['LABEL'] )

  elif (userinput['directive'] == "set") and (userinput['set_option'] == "range"): # set xrange
     [direction,number,axis,commit] = access_axis(userinput['axis'])[0]
     if 'min'     in userinput: axis['MIN'] = userinput['min']
     if 'max'     in userinput: axis['MAX'] = userinput['max']
     if 'minauto' in userinput: axis['MIN'] = None
     if 'maxauto' in userinput: axis['MAX'] = None
     if commit: copy_axis_info_to_gpplot(userinput['axis'], ['MIN','MAX'] )

  elif (userinput['directive'] == "unset") and (userinput['set_option'] == "range"): # unset xrange
     [direction,number,axis,commit] = access_axis(userinput['axis'])[0]
     axis['MIN'] = gp_settings.default_axis['MIN']
     axis['MAX'] = gp_settings.default_axis['MAX']
     if commit: copy_axis_info_to_gpplot(userinput['axis'], ['MIN','MAX'] )

  else:
     gp_error("Internal Error in PyXPlot set command. Please report as a PyXPlot bug with the following text:")
     gp_error("Unhandled user input was: %s"%userinput)

# Directive history

def directive_history(userinput):
  # Work out how many lines to write
  if ('histlines' in userinput):
   Nhist = userinput['histlines']
   if (Nhist < 1):
    gp_error("You can't have fewer than 1 lines of your history!")
    return
   Nhist = min(Nhist, readline.get_current_history_length())
  else:
   Nhist = readline.get_current_history_length()
  for i in range(Nhist):
   item = readline.get_history_item(i)
   print item

# Main Directive Processor

line_combiner = ""

def directive(line, toplevel=True, interactive=False):
  global exitting, line_combiner

  if toplevel: gp_settings.cmd_history.append(line)

  if (line.strip() == ""): return(2) # Blank lines do nothing.
  if (line.strip()[0] == "#"): return(2) # Comment lines also do nothing.

  # Check for \ line splitter
  if (line.strip()[-1] == "\\"):
   line_combiner = line_combiner + line.strip()[:-1]
   return
  line = line_combiner + line
  line_combiner = ""

  # Check for `` shell substitute command
  linesplit = gp_eval.gp_split(line, "`")
  linenew   = ""
  if ((len(linesplit)%2) == 0):
   gp_error("Error: mismatched ` in line.")
   return(1)
  for i in range(len(linesplit)):
   if ((i%2) == 1):
    os.chdir(gp_settings.cwd)
    shell_cmd = os.popen(linesplit[i],"r")
    linesplit[i] = shell_cmd.read().replace('\n',' ')
    shell_cmd.close()
    os.chdir(gp_settings.tempdir)
   linenew = linenew + linesplit[i]
  line = linenew

  # Can use ; to pass multiple commands on one line
  if (line.strip()[0] != "!"): # Don't split shell commandlines
   linelist = gp_eval.gp_split(line,'#') # Hash can be used to place comments after commands
   if len(linelist)>1: line=linelist[0]
   linelist = gp_eval.gp_split(line,';')
  else:
   linelist = [line.strip()]
  if (len(linelist) > 1):
   for i in range(len(linelist)):
    directive(linelist[i], False, interactive)
   return(2) 

  line     = line.strip() # Get rid of leading/trailing spaces
  linelist = line.split()
  if (len(linelist) < 1): return(2)

  # Pass command to parser
  command = gp_parser.parse(line,gp_userspace.variables)

  if (command == None): return(1) # Syntax error

  if (command['directive'] == "unrecognised"): # Unrecognised command

    if   (re.match(r'([A-Za-z]\w*)(\([^()]*\))([^=]*)=(.*)',line.strip()) != None): # f(x) = ...
     t =  re.match(r'([A-Za-z]\w*)(\([^()]*\))([^=]*)=(.*)',line.strip())
     try:
      gp_userspace.gp_function_declare(line)
     except KeyboardInterrupt: raise
     except:
      gp_error("Error defining function %s:"%t.group(1))
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    else:
      gp_error(gp_text.invalid%line) # invalid cmd
      return(1)

  elif (command['directive'] == "var_set"):                   # x = number/string
    try:
      if 'value' in command: gp_userspace.gp_variable_set(command['varname'], command['value'])
      else:                  gp_userspace.gp_variable_del(command['varname'])
    except KeyboardInterrupt: raise
    except:
      gp_error("Error defining variable %s:"%command['varname'])
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "var_set_regex"):     # x =~ regular expression
    try: gp_userspace.gp_variable_re(command['varname'], command['regex'])
    except KeyboardInterrupt: raise
    except:
      gp_error("Error defining variable %s:"%command['varname'])
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "exec"):         # exec
    for exec_line in command['command'].split("\n"):
      directive(exec_line)
  elif (command['directive'] == "quit"):         # exit / quit
    exitting = 1
    return(0)
  elif (command['directive'] == "pling"):        # the ! command
    os.chdir(gp_settings.cwd)
    os.system(command['cmd']) # Execute command in user's cwd
    os.chdir(gp_settings.tempdir)
  elif (command['directive'] == "cd"):           # the cd command
    for subdict in command['path']:
     new_dir = glob.glob(os.path.join(gp_settings.cwd, subdict['directory']))
     if (len(new_dir) == 0):
      gp_error("Error: Directory '%s' could not be found."%subdict['directory'])
     else:
      gp_settings.cwd = new_dir[0]
  elif (command['directive'] == "pwd"):          # the pwd command
    gp_report(gp_settings.cwd)
  elif (command['directive'] == "help"):         # help / ?
    gp_help.directive_help(command, interactive)
  elif (command['directive'] == "history"):
    directive_history(command)
  elif (command['directive'] == "load"):         # load
    main_loop([command['filename']])
  elif (command['directive'] == "save"):         # save
    try:
     savefile = open(os.path.join(gp_settings.cwd, os.path.expanduser(command['filename'])),"w")
     for line in gp_settings.cmd_history[:-1]: savefile.write(line+"\n")
     savefile.close()
    except KeyboardInterrupt: raise
    except:
     gp_error("Error writing output to file '%s':"%command['filename'])
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "set_error"):    # set with no set option
    if 'set_option' in command: gp_error("Error: unrecognised set option '%s'."%command['set_option'])
    elif not interactive: gp_error("Error: set command detected with no set option following it.")
    if interactive: gp_error(gp_text.set_noword)
  elif (command['directive'] == "set"):          # set
    directive_set_unset(command)
  elif (command['directive'] == "unset_error"):  # unset with no set option
    if 'set_option' in command: gp_error("Error: unrecognised set option '%s'."%command['set_option'])
    elif not interactive: gp_error("Error: set command detected with no set option following it.")
    if interactive: gp_error(gp_text.unset_noword)
  elif (command['directive'] == "unset"):        # unset
    directive_set_unset(command)
  elif (command['directive'] == "show"):         # show
    directive_show(command['setting_list'])
  elif (command['directive'] == "fit"):          # fit
    if (len(command['operands,'])>0):
     gp_warning("Syntax 'fit f(x)...' is supported by PyXPlot for gnuplot compatibility, but is deprecated. 'fit f() ...' is prefered.")
    try:
     gp_fit.directive_fit(command,gp_userspace.variables)
    except KeyboardInterrupt: raise
    except:
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "spline"):       # spline
    try:
     gp_spline.directive_spline(command,gp_userspace.variables)
    except KeyboardInterrupt: raise
    except:
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "histogram"):    # histogram
    try:
     gp_histogram.directive_histogram(command,gp_userspace.variables,gp_settings.settings)
    except KeyboardInterrupt: raise
    except:
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  elif (command['directive'] == "tabulate"):    # tabulate
    try:
     gp_tabulate.directive_tabulate(command,gp_userspace.variables,gp_settings.settings)
    except KeyboardInterrupt: raise
    except:
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

  elif (command['directive'] == "plot"):         # plot
    gp_canvas.directive_plot(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,
                           gp_settings.axes,gp_settings.labels,gp_settings.arrows,0,interactive)
  elif (command['directive'] == "replot"):       # replot
    gp_canvas.directive_plot(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,
                           gp_settings.axes,gp_settings.labels,gp_settings.arrows,1,interactive)
  elif (command['directive'] == "text"):         # text
    gp_canvas.directive_text(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,interactive)
  elif (command['directive'] == "arrow"):        # arrow
    gp_canvas.directive_arrow(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,interactive)
  elif (command['directive'] == "jpeg"):         # jpeg
    gp_canvas.directive_jpeg(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,interactive)
  elif (command['directive'] == "eps"):          # eps
    gp_canvas.directive_eps(command,gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,interactive)
  elif (command['directive'] == "clear"):        # clear
    gp_canvas.plotorder_clear()
    gp_children.send_command_to_csa("A","")
  elif (command['directive'] == "reset"):        # reset
    gp_settings.settings              = gp_settings.settings_default.copy()
    gp_settings.labels                = {}
    gp_settings.arrows                = {}
    gp_settings.default_new_axis      = gp_settings.default_axis.copy()
    gp_settings.settings['GRIDAXISX'] = gp_settings.settings_default['GRIDAXISX'][:]
    gp_settings.settings['GRIDAXISY'] = gp_settings.settings_default['GRIDAXISY'][:]
    gp_settings.latex_preamble        = gp_settings.default_latex_preamble
    gp_settings.axes = {'x':{1:gp_settings.default_axis.copy()},
                        'y':{1:gp_settings.default_axis.copy()},
                        'z':{1:gp_settings.default_axis.copy()} }

  elif (command['directive'] == "edit"):         # edit
    if (gp_settings.settings_global['MULTIPLOT'] != 'ON'):
     gp_error("Error: Can only edit plots when in multiplot mode.")
    else:
     editno = command['editno']
     if   (editno >= len(gp_canvas.multiplot_plotdesc)) or (editno < 0):
      gp_error("Error: Attempt to edit a multiplot plot with index %d -- no such plot."%editno)
     elif (gp_canvas.multiplot_plotdesc[editno]["itemtype"] != "plot"):
      gp_error("Error: Attempt to edit a multiplot item which is not a plot. The edit command can only act on plots.")
     else:
      gp_canvas.replot_focus = editno
      gp_settings.settings = gp_canvas.multiplot_plotdesc[editno]['settings'].copy() # Reset all settings to those from this multiplot item
      gp_canvas.plotlist     = gp_canvas.multiplot_plotdesc[editno]['plotlist'][:]
      gp_settings.labels   = gp_canvas.multiplot_plotdesc[editno]['labels'].copy()
      gp_settings.arrows   = gp_canvas.multiplot_plotdesc[editno]['arrows'].copy()
      gp_settings.axes     = { 'x':{},'y':{},'z':{} } # Likewise for axis settings
      gp_canvas.axes_this    = { 'x':{},'y':{},'z':{} }
      for [direction,axis_list_to] in gp_settings.axes.iteritems():
       for [number,axis] in gp_canvas.multiplot_plotdesc[editno]['axes'][direction].iteritems():
        axis_list_to[number] = axis['SETTINGS'].copy()
        gp_canvas.axes_this[direction][number] = {'SETTINGS':axis['SETTINGS'].copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  elif (command['directive'] == "delete"):       # delete
    if (gp_settings.settings_global['MULTIPLOT'] != 'ON'):
     gp_error("Error: Can only delete items when in multiplot mode.")
    else:
     for dn_dict in command['deleteno,']:
      deleteno = dn_dict['number']
      if (deleteno >= len(gp_canvas.multiplot_plotdesc)) or (deleteno < 0):
       gp_error("Error: Attempt to delete multiplot item with index %d -- no such item."%deleteno)
      else:
       if (gp_canvas.multiplot_plotdesc[deleteno]['deleted'] == 'ON'): gp_warning("Warning: Attempt to delete a multiplot item which is already deleted.")
       else: gp_canvas.multiplot_plotdesc[deleteno]['deleted'] = 'ON' # Set delete flag on item
       try:
        if (gp_settings.settings_global['DISPLAY'] == "ON"):
         gp_plot.multiplot_plot(gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,gp_canvas.multiplot_plotdesc) # Refresh display
       except KeyboardInterrupt: raise
       except:
        gp_error("Error: Problem encountered whilst refreshing display after delete operation.")
        gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

  elif (command['directive'] == "undelete"):     # undelete
    if (gp_settings.settings_global['MULTIPLOT'] != 'ON'):
     gp_error("Error: Can only undelete items when in multiplot mode.")
    else:
     for dn_dict in command['undeleteno,']:
      deleteno = dn_dict['number']
      if (deleteno >= len(gp_canvas.multiplot_plotdesc)) or (deleteno < 0):
       gp_error("Error: Attempt to undelete multiplot item with index %d -- no such item."%deleteno)
      else:
       if (gp_canvas.multiplot_plotdesc[deleteno]['deleted'] != 'ON'): gp_warning("Warning: Attempt to undelete a multiplot item which isn't deleted.")
       else: gp_canvas.multiplot_plotdesc[deleteno]['deleted'] = 'OFF' # Unset delete flag on a plot
       try:
        if (gp_settings.settings_global['DISPLAY'] == "ON"):
         gp_plot.multiplot_plot(gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,gp_canvas.multiplot_plotdesc) # Refresh display
       except KeyboardInterrupt: raise
       except:
        gp_error("Error: Problem encountered whilst refreshing display after undelete operation.")
        gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

  elif (command['directive'] == "move"):         # move
    if (gp_settings.settings['MULTIPLOT'] != 'ON'):
     gp_error("Error: Can only move items when in multiplot mode.")
    else:
     moveno = command['moveno']
     if (moveno >= len(gp_canvas.multiplot_plotdesc)) or (moveno < 0):
      gp_error("Error: Attempt to move a multiplot item with index %d -- no such item."%moveno)
     else:
      if (gp_canvas.multiplot_plotdesc[moveno]['itemtype'] == 'plot'): # Plots store their positions in settings -> origin
       gp_canvas.multiplot_plotdesc[moveno]['settings']['ORIGINX'] = command['x']
       gp_canvas.multiplot_plotdesc[moveno]['settings']['ORIGINY'] = command['y']
      else:
       gp_canvas.multiplot_plotdesc[moveno]['x_pos'] = command['x'] # All other multiplot items store positions in separate settings
       gp_canvas.multiplot_plotdesc[moveno]['y_pos'] = command['y']
      try:
       if (gp_settings.settings_global['DISPLAY'] == "ON"):
        gp_plot.multiplot_plot(gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,gp_canvas.multiplot_plotdesc) # Refresh display
      except KeyboardInterrupt: raise
      except:
       gp_error("Error: Problem encountered whilst refreshing display after move operation.")
       gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

  elif (command['directive'] == "refresh"):      # refresh
    try:
      if (gp_settings.settings_global['DISPLAY'] == "ON"):
        gp_plot.multiplot_plot(gp_settings.linestyles,gp_userspace.variables,gp_settings.settings,gp_canvas.multiplot_plotdesc) # Refresh display
    except KeyboardInterrupt: raise
    except:
     gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
    return

  elif (command['directive'] == "print"):        # print
   printstring = ""
   for subdict in command['print_list,']:
    if 'expression' in subdict:
     printstring += "%s "%subdict['expression']
    if 'string' in subdict:
     printstring += "%s "%subdict['string']
   gp_report(printstring)

  else:
    gp_error(gp_text.invalid%linelist[0])        # invalid cmd
    return(1)
  return (0)

def Interactive():   # Interactive PyXPlot terminal
  global exitting,line_combiner,SCIPY_ABSENT
  exitting=0
  if (sys.stdin.isatty() and gp_settings.display_splash): # Only print welcome blurb if running interactively, i.e. not from pipe
    gp_report(gp_text.init)
    if SCIPY_ABSENT:
     gp_warning("Warning: The scipy numerical library for python is not installed. Without this, some features in PyXPlot will be disabled, including the spline and fit commands, and the integration of functions. To enable these features, install scipy and try again.")
     SCIPY_ABSENT = False # Only warn once
  try:
    linenumber=0
    while (exitting==0):
      gp_children.stat_gv_output()
      if (sys.stdin.isatty()):
        try:
          if (line_combiner == ""): prompt = "pyxplot> "
          else                    : prompt = ".......> "
          input_cmd = raw_input(prompt)
          try: directive(input_cmd, interactive=True)
          except KeyboardInterrupt: gp_warning("Received SIGINT. Terminating command.")
        except KeyboardInterrupt: gp_report("") # CTRL-C at command-prompt just gives a new command prompt
      else:
        linenumber=linenumber+1
        gp_error_setstreaminfo(linenumber,"input stream")
        directive(raw_input()) # Don't print command prompt when running from a pipe
  except (KeyboardInterrupt,EOFError): pass # EOFError == CTRL-D
  if sys.stdin.isatty():
   if gp_settings.display_splash: gp_report("\nGoodbye. Have a nice day.")
   else                         : gp_report("")
  gp_error_setstreaminfo(-1,"")
  return

# Main loop

recurse_depth = 0

def main_loop(commandparams):
 global recurse_depth 
 recurse_depth = recurse_depth + 1 # Recursive loading protection
 if (recurse_depth > 10):
  gp_warning("Warning: recursive file loading detecting; load command failing")
  return

 if (len(commandparams) > 0): # Input files specified on commandline
  for i in range(0,len(commandparams)):
   if (commandparams[i] == '-'): # A minus on commandline means interactive
    Interactive()
   elif ((commandparams[i] == '-h') or (commandparams[i] == '--help')):
    gp_report(gp_text.help)
   elif ((commandparams[i] == '-v') or (commandparams[i] == '--version')): # NB: -q option implemented below
    gp_report(gp_text.version)
   else:
    infiles = glob.glob(os.path.join(gp_settings.cwd, os.path.expanduser(commandparams[i])))
    if (len(infiles) == 0):
     gp_error("PyXPlot Error: Could not find command file '%s'"%commandparams[i])
     gp_error("Skipping on to next command file")
    else:
     for infile in infiles:
      exitting=0
      try:
       instream = open(infile,"r")
      except KeyboardInterrupt: raise
      except:
       gp_error("PyXPlot Error: Could not open command file '%s'"%commandparams[i])
       gp_error("Skipping on to next command file")
      else:
       firstline=True # This flips to false after we've processed a non-blank line successfully
       linenumber=0
       for line in instream.readlines():
        linenumber=linenumber+1
        gp_error_setstreaminfo(linenumber,"file '%s'"%infile)
        status = directive(line)
        if (firstline and (status == 1)):
         gp_error("Error on first line of commandfile: Is this is valid script?")
         gp_error("Aborting")
         break
        if (status == 0): firstline=False
        if (exitting==1): break
       gp_error_setstreaminfo(-1,"")
 else: # Otherwise enter interactive mode
   Interactive()

# MAIN ENTRY POINT

# Store path to user's cwd ; but put LaTeX's junk in /tmp for tidiness
gp_settings.cwd = os.getcwd()
os.chdir(gp_settings.tempdir)

# Read user's PyXPlot history, if it exists
if not READLINE_ABSENT:
 readline.set_history_length(1000)
 try: readline.read_history_file(os.path.expanduser("~/.pyxplot_history"))
 except: pass

# Turn off splashscreen if requested (commandline option -q)
while '-q' in sys.argv:
 gp_settings.display_splash = False
 sys.argv.remove('-q')
while '--quiet' in sys.argv:
 gp_settings.display_splash = False
 sys.argv.remove('--quiet')

# Turn on splashscreen if requested (commandline option -V)
while '-V' in sys.argv:
 gp_settings.display_splash = True
 sys.argv.remove('-V')
while '--verbose' in sys.argv:
 gp_settings.display_splash = True
 sys.argv.remove('--verbose')

# Turn on syntax highlighting if requested (commandline option -c)
while '-c' in sys.argv:
 gp_error_setcolour()
 sys.argv.remove('-c')
while '--colour' in sys.argv:
 gp_error_setcolour()
 sys.argv.remove('--colour')
while '--color' in sys.argv:
 gp_error_setcolour()
 sys.argv.remove('--color')

# Turn off syntax highlighting if requested (commandline option -m)
while '-m' in sys.argv:
 gp_error_setnocolour()
 sys.argv.remove('-m')
while '--monochrome' in sys.argv:
 gp_error_setnocolour()
 sys.argv.remove('--monochrome')

# Fix default terminal. If running interatively at any point, use X11_singlewindow.
# If we are going to run entirely from script all the way, default is postscript
if (gp_settings.config_lookup_opt('settings','TERMTYPE','default',gp_settings.termtypes ) == 'default'):
 if  (  ((len(sys.argv)>1) and ("-" not in sys.argv))
     or (gp_version.GHOSTVIEW == '/bin/false')
     or ('DISPLAY' not in os.environ.keys())
     or (len(os.environ['DISPLAY']) < 1)
     or (not sys.stdin.isatty())
     ):
  gp_settings.settings_global['TERMTYPE'] = 'EPS'

if (  ((len(sys.argv)>1) and ("-" not in sys.argv))
   or (not sys.stdin.isatty())
   ):
 gp_settings.interactive = False # A session which will never interact with a user tty; don't use X11 except in persist flavour
else:
 gp_settings.interactive = True

# Loop over all config files passed to us on the commandline
main_loop(sys.argv[1:])

# Close any X11_singlewindow and X11_multiwindow sessions
gp_children.send_command_to_csa("B","")

# Write history file
if not READLINE_ABSENT:
 try: readline.write_history_file(os.path.expanduser("~/.pyxplot_history"))
 except: pass
