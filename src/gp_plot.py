# GP_PLOT.PY
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

# Implementation of plot command

import gp_children
import gp_eval
import gp_datafile
import gp_settings
import gp_spline
from gp_autocomplete import *
from gp_error import *
import gp_math
import gp_version
import gp_postscript
import gp_ticker
import gp_userspace
import gp_histogram

import os
import sys
from math import *
import glob
import operator
import exceptions
import re
from pyx import *

# --------------------------
# This is a temporary piece of sickness. Remove ASAP.
# Fix keys so that we can move them by (x,y) cm

class graph_pyxplot(graph.graphxy):
    def dokey(self):
        if self.did(self.dokey):
            return
        self.dobackground()
        self.dostyles()
        if self.key is not None:
            c = self.key.paint(self.plotitems)
            bbox = c.bbox()
            def parentchildalign(pmin, pmax, cmin, cmax, pos, dist, inside):
                ppos = pmin+0.5*(cmax-cmin)+dist+pos*(pmax-pmin-cmax+cmin-2*dist)
                cpos = 0.5*(cmin+cmax)+(1-inside)*(1-2*pos)*(cmax-cmin+2*dist)
                return ppos-cpos
            if bbox:
                x = parentchildalign(self.xpos_pt, self.xpos_pt+self.width_pt,
                                     bbox.llx_pt, bbox.urx_pt,
                                     self.key.hpos, unit.topt(self.key.hdist), self.key.hinside)
                y = parentchildalign(self.ypos_pt, self.ypos_pt+self.height_pt,
                                     bbox.lly_pt, bbox.ury_pt,
                                     self.key.vpos, unit.topt(self.key.vdist), self.key.vinside)
                self.insert(c, [trafo.translate_pt(x, y), trafo.translate(self.KEY_XOFF,self.KEY_YOFF)])

# --------------------------

# Stores the number of lines on our graph. PyX gets unhappy when this is zero.
plot_counter = 0     # Used for X11 terminal, to give each plot output an individual name

# Counters used to cycle plot styles
linecount = 1 # Counts how many lines have been plotted; used to cycle line styles.
ptcount   = 1 # As above; used to cycle point styles
colourcnt = 1 # As above; used to cycle colours
withstate = 0 # State parameter used when processing input after the word "with"

# Used to count how many lines have gone onto graph. If zero, be careful.... PyX crashes when producing an empty key
successful_plot_operations   = {}
unsuccessful_plot_operations = {}

# Used to store the last datafile filename, to make the '' shorthand work for plotting one datafile in several ways
last_datafile_filename = ''

# Only warn user once about the using modifier when plotting functions
using_use_warned = False

# COORD_TRANSFORM(): Transform from "first", "second" coord systems, etc, into canvas coordinates

def coord_transform(g, axes, systx, systy, x0, y0):
  g.dolayout()

  axisx = axisy = None
  testx = re.match(r"axis(\d\d*)$",systx)
  testy = re.match(r"axis(\d\d*)$",systy)
  if (testx != None): axisx = int(testx.group(1))
  if (testy != None): axisy = int(testy.group(1))

  # Transform x coordinate
  if   (systx in ['graph', 'screen']):
   x = g.pos(x=axes['x'][1]['MIN_RANGE'],y=1.0,xaxis=axes['x'][    1]['AXIS'],yaxis=axes['y'][1]['AXIS'])[0] + x0
  elif ((systx == "second") and (2 in axes['x'])):
   x = g.pos(x=                       x0,y=1.0,xaxis=axes['x'][    2]['AXIS'],yaxis=axes['y'][1]['AXIS'])[0]
  elif ((testx != None) and (axisx in axes['x'])):
   x = g.pos(x=                       x0,y=1.0,xaxis=axes['x'][axisx]['AXIS'],yaxis=axes['y'][1]['AXIS'])[0]
  else:
   if  (systx != "first") :
    gp_warning("Warning -- attempt to use x axis '%s' when it doesn't exist... reverting to 'first'."%systx)
   x = g.pos(x=                       x0,y=1.0,xaxis=axes['x'][    1]['AXIS'],yaxis=axes['y'][1]['AXIS'])[0]

  # Transform y coordinate
  if   (systy in ['graph', 'screen']):
   y = g.pos(x=1.0,y=axes['y'][1]['MIN_RANGE'],xaxis=axes['x'][1]['AXIS'],yaxis=axes['y'][    1]['AXIS'])[1] + y0
  elif ((systy == "second") and (2 in axes['y'])):
   y = g.pos(x=1.0,y=                       y0,xaxis=axes['x'][1]['AXIS'],yaxis=axes['y'][    2]['AXIS'])[1]
  elif ((testy != None) and (axisy in axes['y'])):
   y = g.pos(x=1.0,y=                       y0,xaxis=axes['x'][1]['AXIS'],yaxis=axes['y'][axisy]['AXIS'])[1]
  else:
   if  (systy != "first"):
    gp_warning("Warning -- attempt to use y axis '%s' when it doesn't exist... reverting to 'first'."%systy)
   y = g.pos(x=1.0,y=                       y0,xaxis=axes['x'][1]['AXIS'],yaxis=axes['y'][    1]['AXIS'])[1]

  return [x,y]

# MULTIPLOT_PLOT(): The main plotting engine. Plots whatever is in the current list "multiplot_plotdesc"

def multiplot_plot(linestyles,vars,settings,multiplot_plotdesc):
  global plot_counter
  global successful_plot_operations, unsuccessful_plot_operations

  successful_plot_operations   = {} # Make a list of which plots have anything plotted on them.
  unsuccessful_plot_operations = {} # A list of any plot operations which in some way produced an error

  data_tables = {} # Contains data to be plotted on each multiplot item; indexed by multiplot number

  if not "OFF" in [ x['deleted'] for x in multiplot_plotdesc ]:
   gp_warning("Nothing to plot!")
   return unsuccessful_plot_operations

  # Prepare PyX
  pyx_texter_cleanup()

  # We make a canvas on which to put our graph.
  # This serves two purposes: first, we can then put our arrows etc on top of gridlines (by default PyX puts them under)
  # secondly, we use it to overlay multiplot plots
  multiplot_canvas = canvas.canvas()

  # Multiplot all of our multiplot items
  # NB, in the following, we do work out axes even for deleted plots, as they may be linkaxesed to.

  # Step 1: For each plot in our multiplot list, we work out the ranges of the data, to decide how to autoscale.
  #         This is achieved with a dry-run of the plotting process.
  for this_plotdesc in [x for x in multiplot_plotdesc if x['itemtype'] == 'plot']:
   [Mplotlist, Mkey, Msettings, Mlabels, Marrows, Mdeleted, Maxes_this, multiplot_number] = [ this_plotdesc[x] for x in ['plotlist', 'key', 'settings', 'labels', 'arrows', 'deleted', 'axes', 'number'] ]
   any_autoscaling_axes = 0
   for [direction,axis_list] in Maxes_this.iteritems():
    for [number,axis] in axis_list.iteritems():
     axis['MIN_USED'] = axis['SETTINGS']['MIN']
     axis['MAX_USED'] = axis['SETTINGS']['MAX']
     axis['AXIS']     = None
     axis['LINKINFO'] = {}

     if (axis['SETTINGS']['LOG'] == "ON"):
      if (axis['MIN_USED'] != None) and (axis['MIN_USED'] <= 0.0):
       axis['MIN_USED'] = None
       gp_warning("Warning: Log axis %s%d set with range minimum < 0 -- this is impossible, so autoscaling instead."%(direction,number))
      if (axis['MAX_USED'] != None) and (axis['MAX_USED'] <= 0.0):
       axis['MAX_USED'] = None
       gp_warning("Warning: Log axis %s%d set with range maximum < 0 -- this is impossible, so autoscaling instead."%(direction,number))

     if ((axis['MIN_USED'] == None) or (axis['MIN_USED'] == None)):
      any_autoscaling_axes = 1
   # If we have some autoscaling axes on this plot, we need to check out the range of the data, otherwise not.
   if ((any_autoscaling_axes == 1) and (Mdeleted != 'ON')):
    g = None # We have no graph.... yet
    data_tables[multiplot_number] = dataset_tabulate_axes_autoscale(multiplot_number,Mplotlist,Msettings,Maxes_this,linestyles,vars)

  # Step 2: Propagate range information from linked axes to their parent axes.
  # Repeat twice, as if plots B and C both link to A, and plot B causes plot A's scale to change, we want to
  # propagate that to any functions which evaluate on rasters over plot C.
  for dummy in [0,1]:
   for this_plotdesc in [x for x in multiplot_plotdesc if x['itemtype'] == 'plot']:
    [Mplotlist, Mkey, Msettings, Mlabels, Marrows, Mdeleted, Maxes_this, multiplot_number] = [ this_plotdesc[x] for x in ['plotlist', 'key', 'settings', 'labels', 'arrows', 'deleted', 'axes', 'number'] ]
    plot_dataset_makeaxes_multipropagate(multiplot_number, Msettings, Maxes_this, Mdeleted, multiplot_plotdesc)

  # Now plot everything in order of its appearance in multiplot_plotdesc
  for this_plotdesc in multiplot_plotdesc:
    if (len(multiplot_plotdesc) < 2): plotname = ""
    else                            : plotname = " %d"%this_plotdesc['number']

    if (this_plotdesc['itemtype'] == "plot"): # PLOT A GRAPH
     try:
      [Mplotlist, Mkey, Msettings, Mlabels, Marrows, Mdeleted, Maxes_this, multiplot_number] = [ this_plotdesc[x] for x in ['plotlist', 'key', 'settings', 'labels', 'arrows', 'deleted', 'axes', 'number'] ]

      # Set up the plot's key
      if (Msettings['KEY'] == "ON"):
        if Msettings['KEYPOS'] not in gp_settings.key_positions:
          gp_error("Internal Error: Cannot work out where key is.... defaulting to top-right")
          [hpos,vpos,hinside,vinside] = [1.0, 1.0, 1, 1]
        else:
          [hpos,vpos,hinside,vinside] = gp_settings.key_positions[Msettings['KEYPOS']]

        # Now deal with horizontal and vertical offsets for the key, which are special in "outside" and "below" cases
        if (Msettings['KEYPOS'] == "BELOW"):
          # Count number of x-axes along bottom of plot, and shift title to be below them all
          number_bottom_axes = 0
          for [number,xaxis] in Maxes_this['x'].iteritems():
            if ((number % 2) == 1): number_bottom_axes = number_bottom_axes + 1
          vdist = 1.90 * number_bottom_axes - 0.25
          hdist = 0.6*unit.v_cm
        elif (Msettings['KEYPOS'] == "ABOVE"):
          # Count number of x-axes along top of plot, and shift title to be above them all
          number_top_axes = 0
          for [number,xaxis] in Maxes_this['x'].iteritems():
            if ((number % 2) == 0): number_top_axes = number_top_axes + 1
          vdist = 1.90 * number_top_axes - 0.25
          hdist = 0.6*unit.v_cm
          if (vdist < 0): vdist=0.5
        elif (Msettings['KEYPOS'] == "OUTSIDE"):
          number_right_axes = 0
          for [number,xaxis] in Maxes_this['y'].iteritems():
            if ((number % 2) == 0): number_right_axes = number_right_axes + 1
          hdist = 0.6*unit.v_cm + 2.00 * number_right_axes - 0.75*(number_right_axes == 1)
          vdist = 0.6*unit.v_cm
        else:
          hdist = 0.6*unit.v_cm
          vdist = 0.6*unit.v_cm

        Mkey = graph.key.key(pos=None,hpos=hpos,vpos=vpos,hdist=hdist,vdist=vdist,hinside=hinside,vinside=vinside,columns=Msettings['KEYCOLUMNS'],textattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]])
        graph_pyxplot.KEY_XOFF = Msettings['KEY_XOFF'] # THIS IS SICK!!!
        graph_pyxplot.KEY_YOFF = Msettings['KEY_YOFF']
      else:
        Mkey = None
      multiplot_plotdesc[multiplot_number]['key'] = Mkey

      # Step 3: Make all of our axes which are not linked axes.
      plot_dataset_makeaxes_makenonlink   (Msettings, Maxes_this)
   
      # Step 4: Make all of our axes which are linked axes, linking them to the ones that we've just created.
      plot_dataset_makeaxes_makelinked    (Msettings, Maxes_this, multiplot_plotdesc)
   
      # Step 5: Clean up any linked axes which possibly went wrong, making normal axes instead.
      # For example: circularly defined linked axes are quite bad.
      plot_dataset_makeaxes_makenonlink   (Msettings, Maxes_this)
   
      # Step 6: Now at last we plot everything up properly!
      g = plot_dataset_makeaxes_setupplot(multiplot_number, Msettings, Mkey, Maxes_this)
      if (Mdeleted != 'ON'): # Don't plot items which have been deleted -- we do make plot object above, to anchor axes which may be linked.
        if (g == None): continue                                                                            # Ooops... *That* didn't really work....
        plot_tabulated_data(g,Mplotlist,data_tables[multiplot_number]) # Now do plotting proper.
   
        # We now transfer graph onto our multiplot canvas, and draw arrows/labels on top of it as required
        multiplot_canvas.insert(g)
   
        # Print title of plot, if we have one
        if (len(Msettings['TITLE']) > 0):
          # Count number of x-axes along top of plot, and shift title to be above them all
          number_top_axes = 0
          for [number,xaxis] in Maxes_this['x'].iteritems():
           if ((number % 2) == 0): number_top_axes = number_top_axes + 1
          vertical_pos = g.height + 0.3 + Msettings['TIT_YOFF'] + Msettings['ORIGINY']
          if (number_top_axes > 0): vertical_pos = vertical_pos + 1.1
          if (number_top_axes > 1): vertical_pos = vertical_pos + 1.85 * (number_top_axes - 1)
          horizontal_pos = g.width/2 + Msettings['TIT_XOFF'] + Msettings['ORIGINX']
          try:
           texter = text.texrunner() # Make a new texrunner instance, so that incorrect LaTeX doesn't screw up default texrunner
           pyx_texrunner_init(texter)
           textitem = texter.text(horizontal_pos, vertical_pos, Msettings['TITLE'], [text.halign.center, text.valign.bottom, text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]])
           multiplot_canvas.insert(textitem)
          except KeyboardInterrupt: raise
          except:
           gp_error("Error printing title of plot%s: Incorrect LaTeX possibly?"%plotname)
           gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
           unsuccessful_plot_operations[multiplot_number] = 'ON'
   
        # Print text labels
        try:
          for dummy,(textstr,systx,x,systy,y,rotation,colour,texthal,textval,textsize) in Mlabels.iteritems():
            [x,y] = coord_transform(g, Maxes_this, systx, systy, x, y)
            if   (texthal == 'Centre'): halign = text.halign.center
            elif (texthal == 'Right' ): halign = text.halign.right
            else                      : halign = text.halign.left
            if   (textval == 'Top'   ): valign = text.valign.top
            elif (textval == 'Centre'): valign = text.valign.middle
            else                      : valign = text.valign.bottom

            user_input = with_words_cleanup({'colour':colour},{'linetype':1},Msettings,linestyles,vars,True)
            colour     = gp_settings.pyx_colours[user_input['colour']]

            texter = text.texrunner() # Make a new texrunner instance, so that incorrect LaTeX doesn't screw up default texrunner
            pyx_texrunner_init(texter)
            textitem = texter.text(x, y, textstr, [halign,valign,text.size(textsize),colour,trafo.rotate(rotation,0,0)])
            multiplot_canvas.insert(textitem)
        except KeyboardInterrupt: raise
        except:
          gp_error("Error printing labels on plot%s:"%plotname)
          gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
          unsuccessful_plot_operations[multiplot_number] = 'ON'
   
        # Print arrows
        try:
          for dummy,(systx0,x0,systy0,y0,systx1,x1,systy1,y1,arrow_style) in Marrows.iteritems():
           [x0,y0] = coord_transform(g, Maxes_this, systx0, systy0, x0, y0)
           [x1,y1] = coord_transform(g, Maxes_this, systx1, systy1, x1, y1)
           arrow_style = with_words_cleanup(arrow_style,{'linetype':1},Msettings,linestyles,vars,True)
           if 'arrow_style' in arrow_style:
            if   arrow_style['arrow_style'] == "head"   : arrow_style_list = [deco.earrow]
            elif arrow_style['arrow_style'] == "nohead" : arrow_style_list = []
            elif arrow_style['arrow_style'] == "twohead": arrow_style_list = [deco.barrow, deco.earrow]
            else: assert False, "Internal error: unrecognised setting of arrow_style['arrow_style']"
           else:
            arrow_style_list = [deco.earrow.normal] # Default style is 'head'
  
           # Arrows which go nowhere don't have a direction, and cause PyX to become unhappy... so revert to 'nohead' style
           if ((x0 == x1) and (y0 == y1)): arrow_style_list = []
 
           if ((gp_settings.settings_global['COLOUR'] == 'ON') and (arrow_style['colour'] != "gp_auto")):
            colour = gp_settings.pyx_colours[arrow_style['colour']]  # Use requested colour, if specified
           else:
            colour = color.grey.black                               # If monochrome or no specified colour, then set colour to black

           # Set size of arrow head
           arrow_size = unit.v_pt*6*arrow_style['linewidth']
           for i in range(len(arrow_style_list)):
            arrow_style_list[i] = arrow_style_list[i](size=arrow_size)

           arrow_style_list.append(gp_settings.linestyle_list[(arrow_style['linetype']-1)%len(gp_settings.linestyle_list)])
           arrow_style_list.append(plot_linewidth(arrow_style['linewidth']))
           arrow_style_list.append(colour)
           multiplot_canvas.stroke(path.line(x0,y0,x1,y1),arrow_style_list)
        except KeyboardInterrupt: raise
        except:
          gp_error("Error printing arrows on plot%s:"%plotname)
          gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
          unsuccessful_plot_operations[multiplot_number] = 'ON'

     except KeyboardInterrupt: raise
     except:
      gp_error("Error printing plot%s:"%plotname)
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
      unsuccessful_plot_operations[multiplot_number] = 'ON'

    elif (this_plotdesc['itemtype'] == "text"): # PRINT MULTIPLOT TEXT LABELS
      [textstr,x,y,Msettings,deleted,rotation,colour,multiplot_number] = [ this_plotdesc[x]
                                        for x in ['text','x_pos','y_pos','settings','deleted','rotation','colour','number'] ]
      if (deleted != 'ON'):
       try:
        if   (Msettings['TEXTHALIGN'] == 'Centre'): halign = text.halign.center
        elif (Msettings['TEXTHALIGN'] == 'Right' ): halign = text.halign.right
        else                                      : halign = text.halign.left
        if   (Msettings['TEXTVALIGN'] == 'Top'   ): valign = text.valign.top
        elif (Msettings['TEXTVALIGN'] == 'Centre'): valign = text.valign.middle
        else                                      : valign = text.valign.bottom

        user_input = with_words_cleanup({'colour':colour},{'linetype':1},Msettings,linestyles,vars,True)
        colour     = gp_settings.pyx_colours[user_input['colour']]

        texter = text.texrunner() # Make a new texrunner instance, so that incorrect LaTeX doesn't screw up default texrunner
        pyx_texrunner_init(texter)
        textitem = texter.text(x, y, textstr, [halign,valign,text.size(Msettings['FONTSIZE']),colour,trafo.rotate(rotation,0,0)])
        multiplot_canvas.insert(textitem)
        del texter
       except KeyboardInterrupt: raise
       except:
        gp_error("Error printing text label%s: Incorrect LaTeX possibly?"%plotname)
        gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
        unsuccessful_plot_operations[multiplot_number] = 'ON'

    elif (this_plotdesc['itemtype'] == "jpeg"): # PRINT MULTIPLOT JPEG IMAGES
      [deleted,x,y,rotation,width,height,filename,multiplot_number] = [ this_plotdesc[x] for x in ['deleted','x_pos','y_pos','rotation','width','height','filename','number'] ]
      if (deleted != 'ON'):
       try:
        fn_glob  = glob.glob(os.path.join(gp_settings.cwd, os.path.expanduser(filename))) # Add path to user's cwd to input directory and glob
        assert len(fn_glob)>0,"FILE_NOT_FOUND"
        multiplot_canvas.insert(bitmap.bitmap(xpos=x,ypos=y,width=width,height=height,image=bitmap.jpegimage(fn_glob[0]),compressmode=None), [trafo.rotate(rotation,x,y)])
       except KeyboardInterrupt: raise
       except:
        gp_error("Error printing jpeg image%s:"%plotname)
        if (sys.exc_info()[0] == exceptions.AttributeError): gp_error("Error: No width or height dimensions for the image were specified. Moreover, the image does not contain any internal indication of physical scale. PyXPlot does not know how to scale this image -- try specifying each 'width' or 'height' on the commandline.")
        elif (sys.exc_info()[0] == exceptions.AssertionError) and (str(sys.exc_info()[1]) == "FILE_NOT_FOUND"): gp_error("Error: jpeg image file '%s' not found"%filename)
        else                                               : gp_error("Error: Problem encountered whilst decoding jpeg file. Is this really a jpeg image?")
        unsuccessful_plot_operations[multiplot_number] = 'ON'

    elif (this_plotdesc['itemtype'] == "eps"): # PRINT MULTIPLOT EPS IMAGES
      [deleted,x,y,rotation,width,height,filename,multiplot_number] = [ this_plotdesc[x] for x in ['deleted','x_pos','y_pos','rotation','width','height','filename','number'] ]
      if (deleted != 'ON'):
       try:
        fn_glob  = glob.glob(os.path.join(gp_settings.cwd, os.path.expanduser(filename))) # Add path to user's cwd to input directory and glob
        assert len(fn_glob)>0,"FILE_NOT_FOUND"
        multiplot_canvas.insert(epsfile.epsfile(x=x,y=y,width=width,height=height,filename=fn_glob[0]), [trafo.rotate(rotation,x,y)])
       except KeyboardInterrupt: raise
       except:
        gp_error("Error printing eps image%s:"%plotname)
        if (sys.exc_info()[0] == exceptions.AssertionError) and (str(sys.exc_info()[1]) == "FILE_NOT_FOUND"): gp_error("Error: eps graphic file '%s' not found"%filename)
        else: gp_error("Error: Problem encountered whilst decoding eps file. Is this really an eps graphic?")
        unsuccessful_plot_operations[multiplot_number] = 'ON'
 
    elif (this_plotdesc['itemtype'] == "arrow"): # PRINT MULTIPLOT ARROWS
      [x0,y0,x1,y1,arrow_style,Msettings,deleted,multiplot_number] = [ this_plotdesc[x] for x in ['x_pos','y_pos','x2_pos','y2_pos','style','settings','deleted','number'] ]
      try:
       if (deleted != 'ON'):
        arrow_style = with_words_cleanup(arrow_style,{'linetype':1},Msettings,linestyles,vars,True)
        if 'arrow_style' in arrow_style:
         if   arrow_style['arrow_style'] == "head"   : arrow_style_list = [deco.earrow]
         elif arrow_style['arrow_style'] == "nohead" : arrow_style_list = []
         elif arrow_style['arrow_style'] == "twohead": arrow_style_list = [deco.barrow, deco.earrow]
         else: assert False, "unrecognised setting of arrow_style['arrow_style']"
        else:
         arrow_style_list = [deco.earrow.normal] # Default style is 'head'

        # Arrows which go nowhere don't have a direction, and cause PyX to become unhappy... so revert to 'nohead' style
        if ((x0 == x1) and (y0 == y1)): arrow_style_list = []

        if ((gp_settings.settings_global['COLOUR'] == 'ON') and (arrow_style['colour'] != "gp_auto")):
         colour = gp_settings.pyx_colours[arrow_style['colour']]  # Use requested colour, if specified
        else:
         colour = color.grey.black                               # If monochrome or no specified colour, then set colour to black

        # Set size of arrow head
        arrow_size = unit.v_pt*6*arrow_style['linewidth']
        for i in range(len(arrow_style_list)):
         arrow_style_list[i] = arrow_style_list[i](size=arrow_size)

        arrow_style_list.append(gp_settings.linestyle_list[(arrow_style['linetype']-1)%len(gp_settings.linestyle_list)])
        arrow_style_list.append(plot_linewidth(arrow_style['linewidth']))
        arrow_style_list.append(colour)
        multiplot_canvas.stroke(path.line(x0,y0,x1,y1),arrow_style_list)
      except KeyboardInterrupt: raise
      except:
       gp_error("Error printing arrow%s:"%plotname)
       gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
       unsuccessful_plot_operations[multiplot_number] = 'ON'

  # Output plot
  try:
   plot_counter = plot_counter + 1
   fname = "pyxplot_" + str(os.getpid()) + "_" + str(plot_counter) + ".eps"
   multiplot_canvas.writeEPSfile(fname)
  except KeyboardInterrupt: raise
  except:
   gp_error("Failed while producing eps output:")
   raise

  if (gp_settings.settings_global['TERMTYPE'][0:3] == "X11"): gp_postscript.epssetname(fname, "PyXPlot")
  else:                                    gp_postscript.epssetname(fname, gp_settings.settings_global['OUTPUT'])

  if (gp_settings.settings_global['LANDSCAPE'] == 'ON'): # Convert file to landscape in place
   gp_postscript.landscape(fname)

  if (gp_settings.settings_global['TERMENLARGE'] == 'ON'): # Enlarge to fit page in place
   gp_postscript.enlarge(fname)

  fname_out = os.path.expanduser(gp_settings.settings_global['OUTPUT'])
  if (fname_out == ""): fname_out = "pyxplot.%s"%gp_settings.settings_global['TERMTYPE'].lower()
  out_fname = os.path.join(gp_settings.cwd, os.path.expanduser(fname_out))

  if (gp_settings.settings_global['TERMTYPE'][0:3] == "X11"):               # X11_singlewindow / X11_multiwindow / X11_persist
   if (gp_version.GHOSTVIEW == '/bin/false'):
     gp_error("Error: An attempt is being made to use X11 terminal for output, but the required package 'ghostview' could not be found when PyXPlot was installed.")
   elif ('DISPLAY' not in os.environ.keys()) or (len(os.environ['DISPLAY']) < 1):
     gp_error("Error: An attempt is being made to use X11 terminal for output, but your DISPLAY environment variable is not set; there is no accessible X11 display.")
   else:
     if not gp_settings.interactive:
       if (gp_settings.settings_global['TERMTYPE'] != "X11_persist"): gp_warning("Warning: An attempt is being made to use the %s terminal in a non-interactive PyXPlot session. This won't work, as the resulting plot window will close immediately when PyXPlot exits. Defaulting to the 'X11_persist' terminal instead"%gp_settings.settings_global['TERMTYPE'])
       csa_command = "2"
     else:
       csa_command = {"X11_singlewindow":"0","X11_multiwindow":"1","X11_persist":"2"}[gp_settings.settings_global['TERMTYPE']]
     gp_children.send_command_to_csa(csa_command,fname)
  elif (gp_settings.settings_global['TERMTYPE'] in ["PS","EPS"]):           # PS output
   if (gp_settings.settings_global['TERMTYPE'] == "PS"):
    gp_postscript.epstops(fname) # If producing printable postscript, do so now
   write_output(fname,out_fname,settings)
  elif (gp_settings.settings_global['TERMTYPE'] == "PDF"):                  # PDF output
   gp_postscript.epstops(fname) # ps2pdf takes printable postscript as input
   command = "ps2pdf %s %s.pdf"%(fname,fname)
   os.system(command)
   write_output("%s.pdf"%fname,out_fname,settings)
  elif (gp_settings.settings_global['TERMTYPE'] == "PNG"):                  # PNG output
   command = "convert -density %f -quality 100 "%gp_settings.settings_global['DPI']
   if (gp_settings.settings_global['TERMINVERT'] == "ON"): command = command + "-negate "
   if (gp_settings.settings_global['TERMTRANSPARENT'] == "ON"):
    if (gp_settings.settings_global['TERMINVERT'] == "ON"): command = command + "-transparent black "
    else                                                  : command = command + "-transparent white "
   if (gp_settings.settings_global['TERMANTIALIAS'] == "ON"): command = command + "-antialias "
   else:                                                      command = command + "+antialias "
   command = command + "%s %s.png"%(fname,fname)
   if (os.system(command) != 0): raise KeyboardInterrupt
   write_output("%s.png"%fname,out_fname,settings)
  elif (gp_settings.settings_global['TERMTYPE'] == "GIF"):                  # GIF output
   command = "convert -density %f -quality 100 "%gp_settings.settings_global['DPI']
   if (gp_settings.settings_global['TERMINVERT'] == "ON"): command = command + "-negate "
   if (gp_settings.settings_global['TERMTRANSPARENT'] == "ON"): 
    if (gp_settings.settings_global['TERMINVERT'] == "ON"): command = command + "-transparent black "
    else                                                  : command = command + "-transparent white "
   if (gp_settings.settings_global['TERMANTIALIAS'] == "ON"): command = command + "-antialias "
   else:                                                      command = command + "+antialias "
   command = command + "%s %s.gif"%(fname,fname)
   if (os.system(command) != 0): raise KeyboardInterrupt
   write_output("%s.gif"%fname,out_fname,settings)
  elif (gp_settings.settings_global['TERMTYPE'] == "JPG"):                  # JPG output
   command = "convert -density %f -quality 100 "%gp_settings.settings_global['DPI']
   if (gp_settings.settings_global['TERMINVERT'] == "ON"): command = command + "-negate "
   if (gp_settings.settings_global['TERMANTIALIAS'] == "ON"): command = command + "-antialias "
   else:                                                      command = command + "+antialias "
   command = command + "%s %s.jpg"%(fname,fname)
   if (os.system(command) != 0): raise KeyboardInterrupt
   write_output("%s.jpg"%fname,out_fname,settings)

  return unsuccessful_plot_operations

# PLOT_DATASET_MAKEAXES__________(): Makes axes for a plot, using the ranges which have been found from 

# PLOT_DATASET_MAKEAXES_MULTIPROPAGATE(): Propagate information from linked axes to parent Re range
def plot_dataset_makeaxes_multipropagate(multiplot_number, Msettings, Maxes_this, Mdeleted, multiplot_plotdesc):
 for [direction, axis_list] in Maxes_this.iteritems():
  if (direction != 'z'): # 2D plots don't have z axes
   for [number,axis] in axis_list.iteritems():

    # Make some basic information about this axis
    if (number == 1): axisname = direction             # x1 axis is called x in PyX
    else            : axisname = direction+str(number) # but x2 axis is called x2 in PyX

    # PyX 0.9 doesn't like having x5 axis without an x3, so we form a numbering system for PyX
    pyx_number = pyx_oddeven = number%2
    if (pyx_number == 0): pyx_number = 2
    for [n2,a2] in axis_list.iteritems():
      if ((n2 < number) and (n2%2 == pyx_oddeven)): pyx_number = pyx_number + 2
    if (pyx_number == 1): axispyxname = direction
    else                : axispyxname = direction+str(pyx_number)

    linkaxis      = 'OFF'
    linkaxis_plot = None
    linkaxis_no   = None

    # Test to see whether it is a linked axis
    test = re.match(r"""linkaxis\s\s*(\d\d*)(\s*,?\s*)(\d*)""", axis['SETTINGS']['LABEL'])  
    if (test != None):
     if (gp_settings.settings_global['MULTIPLOT'] != 'ON'):
      gp_warning("Warning: apparent attempt to create a linked axis when not in multiplot mode... doomed to fail!")
     else:
      try:
       linkaxis_plot = int(test.group(1))
       if (len(test.group(2)) == 0): linkaxis_no = 1
       else                        : linkaxis_no = int(test.group(3))
       if (linkaxis_plot >= len(multiplot_plotdesc)) or (multiplot_plotdesc[linkaxis_plot]['itemtype'] != 'plot'):
        gp_warning("Warning: attempt to create a linked axis to a non-existant plot: %s"%axis['SETTINGS']['LABEL'])
       elif (linkaxis_plot >= multiplot_number):
        gp_warning("Warning: attempt to create a linked axis from plot %d to plot %d; linked axes must link to an earlier plot."%(multiplot_number, linkaxis_plot))
       elif (not linkaxis_no in multiplot_plotdesc[linkaxis_plot]['axes'][direction]):
        gp_warning("Warning: attempt to create a linked axis to %s-axis number %d of plot %d, but this plot has no such axis:\n%s"%(direction,linkaxis_no,linkaxis_plot,axis['SETTINGS']['LABEL']))
       else:
        linkaxis = 'ON'
        # Propagate range information from linked axis to parent axis
        # But only if we're not deleted
        if (axis['MIN_USED'] != None) and ((axis['MIN_USED'] < multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MIN_USED']) or (multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MIN_USED'] == None)) and ((multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['SETTINGS']['LOG'] != "ON") or (axis['MIN_USED'] > 0.0)):
         if (Mdeleted != 'ON'): multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MIN_USED'] = axis['MIN_USED']
        else:
         axis['MIN_USED'] = multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MIN_USED']
        if (axis['MAX_USED'] != None) and (axis['MAX_USED'] > multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MAX_USED']):
         if (Mdeleted != 'ON'): multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MAX_USED'] = axis['MAX_USED']
        else:
         axis['MAX_USED'] = multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MAX_USED']
      except KeyboardInterrupt: raise
      except:
       gp_error("Error whilst reading linkaxis command: %s"%axis['SETTINGS']['LABEL'])
       gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

    # Store information about our linkage status
    axis['LINKINFO']={'LINKED':linkaxis, 'PLOT':linkaxis_plot, 'AXISNO': linkaxis_no, 'AXISNAME':axisname, 'AXISPYXNAME':axispyxname}

# PLOT_DATASET_MAKEAXES_MAKENONLINK(): Make axes which are not linked axes
def plot_dataset_makeaxes_makenonlink(Msettings, Maxes_this):
 for [direction, axis_list] in Maxes_this.iteritems():
  if (direction != 'z'): # 2D plots don't have z axes
   for [number,axis] in axis_list.iteritems():

    if ((axis['LINKINFO']['LINKED'] != 'ON') and (axis["AXIS"] == None)):

     axisname = axis['LINKINFO']['AXISNAME']
     if (axis['SETTINGS']['LOG'] != "ON"): axistype = graph.axis.linear
     else                                : axistype = graph.axis.log

     # If no data on axis, make up a default range
     if (axis['MIN_USED'] == None):
      if (axis['SETTINGS']['LOG'] == 'ON'):
       if (axis['MAX_USED'] != None): axis['MIN_USED'] = axis['MAX_USED'] / 100 # Log axes start from 1
       else                         : axis['MIN_USED'] = 1.0
      else:
       if (axis['MAX_USED'] != None): axis['MIN_USED'] = axis['MAX_USED'] - 20
       else                         : axis['MIN_USED'] = -10.0                  # Lin axes start from -10

     if (axis['MAX_USED'] == None):
      if (axis['SETTINGS']['LOG'] == 'ON'): axis['MAX_USED'] = axis['MIN_USED'] * 100
      else                                : axis['MAX_USED'] = axis['MIN_USED'] + 20

     # If there's no spread of data on the axis, make a spread up
     # We do this even if range is set by user, as it's a stupid thing to do, otherwise.
     if gp_math.isequal(axis['MAX_USED'], axis['MIN_USED'], 1e-6):
      if (axis['SETTINGS']['LOG'] != "ON"):
       axis['MIN_USED'] = axis['MIN_USED'] - max(1.0,1e-6*fabs(axis['MIN_USED']))
       axis['MAX_USED'] = axis['MAX_USED'] + max(1.0,1e-6*fabs(axis['MIN_USED']))
      else:
       if (axis['MIN_USED'] > 1e-300): axis['MIN_USED'] = axis['MIN_USED'] / 10
       if (axis['MAX_USED'] < 1e+300): axis['MAX_USED'] = axis['MAX_USED'] * 10

     # NB: This code may be executed, even if above conditional is not, as MIN_USED and MAX_USED may have been fixed
     # when making raster to plot a function
     if ((axis['SETTINGS']['MIN'] != None) and (axis['SETTINGS']['MIN'] == axis['SETTINGS']['MAX'])):
      gp_warning("Warning: %s-axis set to have minimum and maximum equal; this is probably not sensible."%axisname)
      gp_warning("         Reverting to alternative limits.")

     # Log axes going below zero is *bad* -- protect against it
     if (axis['SETTINGS']['LOG'] == "ON"):
      if (axis['MIN_USED'] <= 0.0):
       axis['MIN_USED'] = 1e-6
       gp_warning("Warning: Log axis %s set with range minimum < 0 -- this is impossible. Reverting to 1e-6 instead."%axisname)
       gp_warning("This should not have happened. Please report as a PyXPlot bug.")
      if (axis['MAX_USED'] <= 0.0):
       axis['MAX_USED'] = 1.0
       gp_warning("Warning: Log axis %s set with range maximum < 0 -- this is impossible. Reverting to 1.0 instead."%axisname)
       gp_warning("This should not have happened. Please report as a PyXPlot bug.")

     # Autoscaled axes scale outwards to nearest round number, which we do now
     axis_min = minprelim = axis['MIN_USED']
     axis_max = maxprelim = axis['MAX_USED']
     if (fabs(minprelim) > gp_math.FLT_MAX): minprelim = gp_math.FLT_MAX * gp_math.sgn(minprelim)
     if (fabs(maxprelim) > gp_math.FLT_MAX): maxprelim = gp_math.FLT_MAX * gp_math.sgn(maxprelim)

     if (axis['SETTINGS']['LOG'] == "ON"):
      minprelim = log10(minprelim)
      maxprelim = log10(maxprelim)

     try:
      OoM = pow(10.0, floor(log10(fabs(maxprelim - minprelim))))
      minauto = floor(minprelim / OoM) * OoM
      maxauto = ceil (maxprelim / OoM) * OoM
     except KeyboardInterrupt: raise
     except:
      gp_error("Error whilst working out range of axis %s:"%axisname)
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
      minauto = 1 ; maxauto = 10 # Do anything we can to rescue the situation!

     if (axis['SETTINGS']['LOG'] == "ON"):
      if (fabs(minauto) > gp_math.EXP_MAX): minauto = gp_math.EXP_MAX * gp_math.sgn(minauto)
      if (fabs(maxauto) > gp_math.EXP_MAX): maxauto = gp_math.EXP_MAX * gp_math.sgn(maxauto)
      minauto = max(pow(10.0,minauto),1e-300) # Just in case of numerical roundoff issues
      maxauto = max(pow(10.0,maxauto),1e-300)

     if (axis['SETTINGS']['MIN'] == None): axis_min = minauto # Honour hard-coded ranges, otherwise use autoranges
     if (axis['SETTINGS']['MAX'] == None): axis_max = maxauto

     axis['MIN_RANGE'] = axis_min ; axis['MAX_RANGE'] = axis_max

     if ((Msettings['GRID'] == 'ON') and (number in Msettings['GRIDAXIS%s'%direction.capitalize()])): 
      gridalloc = [attr.changelist([gp_settings.pyx_colours[Msettings['GRIDMAJCOLOUR']],
                                    gp_settings.pyx_colours[Msettings['GRIDMINCOLOUR']] ])] # Make gridlines only on specified x/y axes
     else:
      gridalloc = None

     # Work out where ticks go
     if (Msettings['AUTOASPECT'] == "ON"): aspect = 2.0/(1+sqrt(5))
     else                                : aspect = Msettings['ASPECT']

     square = gp_math.isequal(aspect, 1.0)
     if (direction == 'y') and not square: tick_sep_maj = 1.2 ; tick_sep_min = 0.8 ; length_phy = Msettings['WIDTH']*aspect
                                                   # y-axes can have ticks every 1.3cm, by default
     else                                : tick_sep_maj = 2.0 ; tick_sep_min = 0.8 ; length_phy = Msettings['WIDTH']
                                                   # other axes should only have them every 2cm

     if (axis['SETTINGS']['LOG'] == "ON"): tick_list = gp_ticker.log_getticks   (axis, length_phy, tick_sep_maj, tick_sep_min)
     else                                : tick_list = gp_ticker.linear_getticks(axis, length_phy, tick_sep_maj, tick_sep_min)

     axis['TICKS'] = tick_list

     # Now make axis
     try:
      lab = axis['SETTINGS']['LABEL']
      innerticklength = outerticklength = None
      if (axis['SETTINGS']['TICDIR'] in ['INWARD' ,'BOTH']): innerticklength = graph.axis.painter.ticklength.normal
      if (axis['SETTINGS']['TICDIR'] in ['OUTWARD','BOTH']): outerticklength = graph.axis.painter.ticklength.normal
      if (lab[:8] == "nolabels") and ((len(lab)==8) or (lab[8]==":")):
       axis["AXIS"] = axistype(title=lab[9:],min=axis_min,max=axis_max,parter=None,manualticks=tick_list,painter=graph.axis.painter.regular(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],labelattrs=None,titleattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],gridattrs=gridalloc))
      elif (lab[:12] == "nolabelstics") and ((len(lab)==12) or (lab[12]==":")):
       axis["AXIS"] = axistype(title=lab[13:],min=axis_min,max=axis_max,parter=None,manualticks=tick_list,painter=graph.axis.painter.regular(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=None,labelattrs=None,titleattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],gridattrs=gridalloc))
      elif (lab[:9] == "invisible") and ((len(lab)==9) or (lab[9]==":")):
       axis["AXIS"] = axistype(title=lab[10:],min=axis_min,max=axis_max,parter=None,manualticks=tick_list,painter=graph.axis.painter.regular(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=None,tickattrs=None,labelattrs=None,titleattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],gridattrs=gridalloc))
      else:
       axis["AXIS"] = axistype(title=axis['SETTINGS']['LABEL'],min=axis_min,max=axis_max,parter=None,manualticks=tick_list,painter=graph.axis.painter.regular(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],labelattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],titleattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],gridattrs=gridalloc))
     except KeyboardInterrupt: raise
     except:
      gp_error("Error whilst making axis %s -- probably its range is too big:"%axisname)
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
     else:   continue

     # Do our best to rescue a broken situation... by setting range of axis to 1 -> 10.
     try:
      axis_min = 1 ; axis_max = 10
      axis["AXIS"] = axistype(title=axis['SETTINGS']['LABEL'],min=axis_min,max=axis_max,painter=graph.axis.painter.regular(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],labelattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],titleattrs=[text.size(Msettings['FONTSIZE']),gp_settings.pyx_colours[Msettings['TEXTCOLOUR']]],gridattrs=gridalloc))
     except KeyboardInterrupt: raise
     except:
      gp_error("Attempt to rectify broken axis %s also failed:")
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
     continue

# PLOT_DATASET_MAKEAXES_MAKELINKED(): Try to make linked axes
def plot_dataset_makeaxes_makelinked(Msettings, Maxes_this, multiplot_plotdesc):
 for [direction, axis_list] in Maxes_this.iteritems():
  if (direction != 'z'): # 2D plots don't have z axes
   for [number,axis] in axis_list.iteritems():
    if ((axis["AXIS"] == None) and (axis['LINKINFO']['PLOT'] != None) and (axis['LINKINFO']['AXISNO'] != None)):
     axis['LINKINFO']['LINKED'] = 'OFF' # Unset linked axis flag, in case we encounter a problem and this axis needs cleaning up later
     linkaxis_plot = axis['LINKINFO']['PLOT']
     linkaxis_no   = axis['LINKINFO']['AXISNO']

     if (multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]["AXIS"] != None):
      if ((Msettings['GRID'] == 'ON') and (number in Msettings['GRIDAXIS%s'%direction.capitalize()])):
       gridalloc = [attr.changelist([gp_settings.pyx_colours[Msettings['GRIDMAJCOLOUR']],
                                     gp_settings.pyx_colours[Msettings['GRIDMINCOLOUR']] ])] # Make gridlines only on specified x/y axes
      else:
       gridalloc = None
      innerticklength = outerticklength = None
      if (axis['SETTINGS']['TICDIR'] in ['INWARD' ,'BOTH']): innerticklength = graph.axis.painter.ticklength.normal
      if (axis['SETTINGS']['TICDIR'] in ['OUTWARD','BOTH']): outerticklength = graph.axis.painter.ticklength.normal
      tick_list = multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]["TICKS"]
      axis['MIN_RANGE'] = multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MIN_RANGE'] # These values are read later in case of "set label 1 'foo' at screen 0, screen 0"
      axis['MAX_RANGE'] = multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]['MAX_RANGE']
      axis['TICKS'] = tick_list
      axis["AXIS"] = graph.axis.linkedaxis(multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]["AXIS"],painter=graph.axis.painter.linked(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],gridattrs=gridalloc))
      # We make another spare linked axis to use on x2 axis if required (it seems that linked axes cannot be reused...)
      axis["AXIS_SPARE"] = graph.axis.linkedaxis(multiplot_plotdesc[linkaxis_plot]['axes'][direction][linkaxis_no]["AXIS"],painter=graph.axis.painter.linked(innerticklength=innerticklength,outerticklength=outerticklength,basepathattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],tickattrs=[gp_settings.pyx_colours[Msettings['AXESCOLOUR']]],gridattrs=gridalloc))
      if (axis["AXIS"] != None): axis['LINKINFO']['LINKED'] = 'ON' # Linked axis successfully made, there will be no need to clean up.
     else:
      gp_error("Error: cannot link axis to another link axis!")

# PLOT_DATASET_MAKEAXES_SETUPPLOT(): Make graph object, using all of the axes that we have just assigned
def plot_dataset_makeaxes_setupplot(multiplot_number, Msettings, Mkey, Maxes_this):

 axisassign = "" # String listing all of the axes to put onto our plot

 if (Msettings['AUTOASPECT'] == 'ON'):
  ratioassign=""
 else:
  ratioassign="ratio=%f,"%(1.0/Msettings['ASPECT'])
 if (not multiplot_number in successful_plot_operations): Mkey = None # Don't put a key on a plot with no datasets... PyX crashes!

 for [direction, axis_list] in Maxes_this.iteritems():  # Populate axisassign with a list of all axes
  hadaxistwo = False # If user hasn't made a second axis, we manually make one here; allows us to colour it as we wish
  if (direction != 'z'): # 2D plots don't have z axes 
   for [number,axis] in axis_list.iteritems():
    if (axis['LINKINFO']['AXISPYXNAME'] == direction+"2"): hadaxistwo = True
    axisassign = axisassign + axis['LINKINFO']['AXISPYXNAME'] + "=Maxes_this['"+direction+"']["+str(number)+"]['AXIS'],"
   if not hadaxistwo:
    if (axis_list[1]['LINKINFO']['LINKED'] != "ON"): # If axis 1 is not linked, we need to make a copy of it without labels
     if (axis_list[1]['SETTINGS']['LOG'] != "ON"): axistype = 'graph.axis.linear'
     else                                        : axistype = 'graph.axis.log'
     innerticklength = outerticklength = "None"
     if (axis['SETTINGS']['TICDIR'] in ['INWARD' ,'BOTH']): innerticklength = "graph.axis.painter.ticklength.normal"
     if (axis['SETTINGS']['TICDIR'] in ['OUTWARD','BOTH']): outerticklength = "graph.axis.painter.ticklength.normal"
     tick_list = "Maxes_this['"+direction+"'][1]['TICKS']"
     axisassign = axisassign + direction+"2=%s(min=%s,max=%s,parter=None,manualticks=%s,painter=graph.axis.painter.regular(innerticklength=%s,outerticklength=%s,basepathattrs=[gp_settings.pyx_colours['%s']],tickattrs=[gp_settings.pyx_colours['%s']],labelattrs=None,titleattrs=None)),"%(axistype,axis_list[1]['MIN_RANGE'],axis_list[1]['MAX_RANGE'],tick_list,innerticklength,outerticklength,Msettings['AXESCOLOUR'],Msettings['AXESCOLOUR'])
    else:
     axisassign = axisassign + direction+"2=Maxes_this['"+direction+"'][1]['AXIS_SPARE']," # If axis 1 is linked, just use the spare linked axis

 exec "g = graph_pyxplot(width=Msettings['WIDTH'],"+ratioassign+axisassign+"key=Mkey,xpos=%f,ypos=%f)"%(Msettings['ORIGINX'],Msettings['ORIGINY'])
 if (g == None):
   gp_error("Internal error: Failed to produce graph object in PyX.")
 else:
   for [direction, axis_list] in Maxes_this.iteritems():  # Keep a copy of this axis as specific to this particular plot -- a PyX 0.8.1 thing
    if (direction != 'z'): # 2D plots don't have z axes 
     for [number,axis] in axis_list.iteritems():
      axis["AXIS"] = g.axes[axis['LINKINFO']['AXISPYXNAME']]

 return g

# DATASET_TABULATE_AXES_AUTOSCALE():

def dataset_tabulate_axes_autoscale(multiplot_number,Mplotlist,Msettings,Maxes_this,linestyles,vars):
  global linecount, ptcount, colourcnt

  # Counts number of lines/pointsets plotted, so that we can cycle styles
  verb_errors = True
  colourcnt = 1
  linecount = 1
  ptcount   = 1

  data_tables = [None for i in range(len(Mplotlist))]

  # Tabulate / autoscale using datafiles first, to get an idea of the range of the x-axis
  # Tabulate / autoscale using functions second, sampling them over the range that we have now determined
  for [filename_in,handler] in [ [True,tabulate_datafile] , [False,tabulate_function] ]:
   for i in range(len(Mplotlist)):
    plotitem=Mplotlist[i]
    if ('filename' in plotitem)==filename_in:
     try:
      data_tables[i] = handler(multiplot_number,Maxes_this,Msettings,linestyles,plotitem,vars,verb_errors)
      if (data_tables[i] != None):
       for data_table in data_tables[i]:
        [datagrid_cpy_list,axes,axis_x,axis_y,localtitle,stylestr,description,verb_errors] = [data_table[j] for j in ['datagrid_cpy_list','axes','axis_x','axis_y','localtitle','stylestr','description','verb_errors']]
        axes_autoscale(multiplot_number,Msettings,datagrid_cpy_list,axes,axis_x,axis_y,localtitle,stylestr,description,verb_errors)
     except KeyboardInterrupt: raise
     except ValueError: pass

  return data_tables

# PLOT_TABULATED_DATA():
def plot_tabulated_data(g,Mplotlist,data_tables):
 for i in range(len(Mplotlist)):
  plotitem=Mplotlist[i]
  try:
   if (data_tables[i] != None):
    for data_table in data_tables[i]:
     [datagrid_cpy_list,axes,axis_x,axis_y,dx,dxmin,dy,dymin,localtitle,stylelist,description,verb_errors] = [data_table[j] for j in ['datagrid_cpy_list','axes','axis_x','axis_y','dx','dxmin','dy','dymin','localtitle','stylelist','description','verb_errors']]
     plot_dataset(g,datagrid_cpy_list,axes,axis_x,axis_y,dx,dxmin,dy,dymin,localtitle,stylelist,description,verb_errors)
  except KeyboardInterrupt: raise
  except: 
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")

# TABULATE_DATAFILE(): Take datapoints listed in datafile and turn them into a grid of data to pass to PyX
def tabulate_datafile(multiplot_number,axes,settings,linestyles,plotwords,vars,verb_errors):
  global last_datafile_filename

  # Input datafile filename
  datafile = plotwords['filename']

  # axis_x
  if 'axis_x' in plotwords:
   assert plotwords['axis_x'][0] == 'x', "First named axis following the axis modifier in the plot plotwords should be an x-axis"
   axis_x = int(plotwords['axis_x'][1:])
  else: axis_x = 1
  # Create axis if it doesn't already exist
  if (not axis_x in axes['x']): axes['x'][axis_x] = {'SETTINGS':gp_settings.default_new_axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  # axis_y
  if 'axis_y' in plotwords:
   assert plotwords['axis_y'][0] == 'y', "Second named axis following the axis modifier in the plot plotwords should be a y-axis"
   axis_y = int(plotwords['axis_y'][1:])
  else: axis_y = 1
  # Create axis if it doesn't already exist
  if (not axis_y in axes['y']): axes['y'][axis_y] = {'SETTINGS':gp_settings.default_new_axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  # every
  if 'every_list:' in plotwords: every = plotwords['every_list:']
  else                         : every = []

  # index
  if 'index' in plotwords: index = int(plotwords['index'])
  else                   : index = -1 # default

  # title
  if 'title' in plotwords: title = plotwords['title']
  else                   : title = None # None means we get an autotitle

  # notitle
  if 'notitle' in plotwords: title = "" # This means that we really get no title

  # select
  if 'select_criterion' in plotwords: select_criteria = plotwords['select_criterion']
  else                              : select_criteria = ''
  select_cont = True
  if (('select_cont' in plotwords) and (plotwords['select_cont'][0] == 'd')):
   select_cont = False

  # Using rows or columns
  if   'use_rows'    in plotwords: usingrowcol = "row"
  elif 'use_columns' in plotwords: usingrowcol = "col"
  else                           : usingrowcol = "col" # default

  # using
  if 'using_list:' in plotwords: using = [item['using_item'] for item in plotwords['using_list:']]
  else                         : using = []

  # 'with' words cleanup
  plotwords = with_words_cleanup(plotwords,settings['DATASTYLE'],settings,linestyles,vars,verb_errors)

  if (len(datafile) == 0):
    datafile = last_datafile_filename # '' shorthand for last datafile we used
  else:
    last_datafile_filename = datafile

  if datafile=="-":
   datafiles=[datafile] # stdin
  else:
   datafiles = glob.glob(os.path.join(gp_settings.cwd, os.path.expanduser(datafile)))
  datafiles.sort() # Sort list of globbed input filenames into alphabetical order
  userdatafile = datafile

  if (len(datafiles) == 0):
   raise IOError, "Datafile '%s' could not be found."%datafile

  if (len(datafiles) > 10) and (not verb_errors):
   gp_warning("Plotting %d datafiles... this may take a little while..."%len(datafiles))

  tabulated_datasets = [] # If datafiles are being globbed with a wildcard, may have several separate datasets to plot
  for datafile in datafiles: # Plot each datafile in turn
   try:

    # Generate autotitle if we don't have one supplied
    title_this = title # Use title_this, because when we're globbing multiple filenames, we want title to still be None on the next for loop iteration.
    if (title_this == None):
     title_this = "`"+globwithuserpath(datafile,userdatafile)+"' " + title_autostring_generate(every,index,select_criteria,using)
     title_this = title_string_texify(title_this)

    try:
     datafile_totalgrid = gp_datafile.gp_dataread(datafile, index, usingrowcol, using, select_criteria, select_cont, every, vars, plotwords['style'], verb_errors=verb_errors)
    except KeyboardInterrupt: raise
    except:
      if (verb_errors): gp_error("Error reading input datafile '%s'."%datafile)
      raise

    if (len(datafile_totalgrid) < 2): raise IOError, "No datapoints found in file '%s'."%datafile
  
    for data_section in range(1,len(datafile_totalgrid)): # Loop over data sections within index, plotting each as a separate line 
      [rows, columns, datagrid] = datafile_totalgrid[data_section]
 
      # Tabulate dataset
      if (data_section == 1): repeat = 0 # Are we to use same style as previous lump of data we plotted?
      else                  : repeat = 1
      tabulated_datasets.append(tabulate_dataset(multiplot_number,axes,axis_x,axis_y,plotwords,settings,title_this,datagrid,rows,columns,"datafile '%s'"%datafile,repeat,verb_errors))
   except:
    if (verb_errors): gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
  return tabulated_datasets

# GLOBWITHUSERPATH(): Takes a glob result, e.g. /home/dcf21/datafile.dat, and the filename which the user supplied,
# perhaps ~dcf21/dat*.dat, and make a result like ~dcf21/datafile.dat.

def globwithuserpath(globform, userform):
  globbits = globform.split("/")
  userbits = userform.split("/")
  i=0
  while (i<len(userbits)):
    i+=1
    if gwup_canmatch(globbits[-i],userbits[-i]): userbits[-i]=globbits[-i]
    else                                       : break
  outstring=""
  for string in userbits: outstring+=string+"/"
  return outstring[:-1]

def gwup_canmatch(globbit, userbit, gpos=0, upos=0):
  while ((upos >= len(userbit)) or (userbit[upos] != "*")):
    if (upos >= len(userbit)): return True # We've reached the end of the user string
    if ((gpos < len(globbit)) and ((userbit[upos] == "?") or (userbit[upos] == globbit[gpos]))):
      gpos+=1
      upos+=1
      continue # This character matched, let's test next one...
    else:
      return False # This character didn't match...
  for i in range(gpos, len(globbit), 1):
    if gwup_canmatch(globbit, userbit, i, upos+1): # Try and match * with however many characters
      return True
  return False

# TABULATE_FUNCTION(): Take a function which the user has requested to plot, and produce a grid of data to pass to PyX
def tabulate_function(multiplot_number,axes,settings,linestyles,plotwords,vars,verb_errors):
  global using_use_warned

  if plotwords['expression_list:'] == []: return

  # Input functions
  functions = [item['expression'] for item in plotwords['expression_list:'] ]
  xname     = 'x' # We always vary variable x along x axis...
  function_str = ""
  for i in range(len(functions)):
   if i!=0: function_str += ":"
   function_str += functions[i]

  # axis_x
  if 'axis_x' in plotwords:
   assert plotwords['axis_x'][0] == 'x', "First named axis following the axis modifier in the plot plotwords should be an x-axis"
   axis_x = int(plotwords['axis_x'][1:])
  else: axis_x = 1
  # Create axis if it doesn't already exist
  if (not axis_x in axes['x']): axes['x'][axis_x] = {'SETTINGS':gp_settings.default_new_axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  # axis_y
  if 'axis_y' in plotwords:
   assert plotwords['axis_y'][0] == 'y', "Second named axis following the axis modifier in the plot plotwords should be a y-axis"
   axis_y = int(plotwords['axis_y'][1:])
  else: axis_y = 1
  # Create axis if it doesn't already exist
  if (not axis_y in axes['y']): axes['y'][axis_y] = {'SETTINGS':gp_settings.default_new_axis.copy(), 'MIN_USED':None, 'MAX_USED':None, 'AXIS':None}

  # every
  if 'every_list:' in plotwords: every = plotwords['every_list:']
  else                         : every = []

  # index
  if 'index' in plotwords: index = int(plotwords['index'])
  else                   : index = -1 # default

  # title
  if 'title' in plotwords: title = plotwords['title']
  else                   : title = None # None means we get an autotitle

  # notitle
  if 'notitle' in plotwords: title = "" # This means that we really get no title

  # select
  if 'select_criterion' in plotwords: select_criteria = plotwords['select_criterion']
  else                              : select_criteria = ''
  select_cont = True
  if (('select_cont' in plotwords) and (plotwords['select_cont'][0] == 'd')):
   select_cont = False

  # Using rows or columns
  if   'use_rows'    in plotwords: usingrowcol = "row"
  elif 'use_columns' in plotwords: usingrowcol = "col"
  else                           : usingrowcol = "col" # default

  # using
  if 'using_list:' in plotwords:
   if not using_use_warned:
    gp_warning("Warning: The use of the 'using' modifier when plotting functions comes with\nsevere caveats, as the range of x coordinates for which the function will be\ncalculated will continue to correspond to that of the graph's x-axis,\nregardless of what is actually plotted on this axis. Its use with autoscaling\nis especially not recommended. See the section 'General Extensions Beyond\nGnuplot' of the PyXPlot Users' Manual for further details.\n")
    using_use_warned = True
   using = [item['using_item'] for item in plotwords['using_list:']]
  else:
   using = []

  # 'with' words cleanup
  plotwords = with_words_cleanup(plotwords,settings['FUNCSTYLE'],settings,linestyles,vars,verb_errors)

  # Generate autotitle if needed
  if (title == None):
   title = function_str + " " + title_autostring_generate(every,index,select_criteria,using)
   title = title_string_texify(title)

  # Make raster to evaluate function along, between limits of x-axis.
  minimum = axes['x'][axis_x]['MIN_USED']
  maximum = axes['x'][axis_x]['MAX_USED']

  # If no data on axis, make up a default range
  if (minimum == None): 
   if (axes['x'][axis_x]['SETTINGS']['LOG'] == 'ON'):
    if (maximum != None): minimum = maximum / 100 # Log axes start from 1
    else                : minimum = 1.0
   else:
    if (maximum != None): minimum = maximum - 20
    else                : minimum = -10.0         # Lin axes start from -10

  if (maximum == None):
   if (axes['x'][axis_x]['SETTINGS']['LOG'] == 'ON'): maximum = minimum * 100
   else                                             : maximum = minimum + 20

  # For boxes and histeps plot styles, take into account finite width of points
  if (plotwords['style'] in ["boxes", "histeps"]):
   if (settings['BOXWIDTH'] > 0.0): boxwidth = settings['BOXWIDTH']
   else                           : boxwidth = abs(maximum-minimum)/(settings['SAMPLES'] + 1)
   maximum2 = max(minimum,maximum) - boxwidth/2
   minimum2 = min(minimum,maximum) + boxwidth/2
   maximum  = maximum2
   minimum  = minimum2 

  # Finally compute raster
  if (axes['x'][axis_x]['SETTINGS']['LOG'] == 'ON'): xrast = gp_math.lograst(minimum, maximum, settings['SAMPLES'])
  else:                                              xrast = gp_math.linrast(minimum, maximum, settings['SAMPLES'])

  # If we are plotting a histogram we want a special raster that gives us a single point, in the right place, for each bin
  if (plotwords['style'] == "boxes"):
   test = re.match(r"^\s*([A-Za-z]\w*)\s*\(.*\)", functions[0])
   if (test != None):
    plotfunc = test.group(1)
    for funcname in gp_userspace.functions:
     if ((gp_userspace.functions[funcname]['histogram']==True) and (plotfunc==funcname)):  # If the function that we're using is a historgram
      xrast = gp_histogram.histrast(minimum, maximum, axes['x'][axis_x]['SETTINGS']['LOG'], funcname)

  # Now evaluate functions
  totalgrid = gp_datafile.gp_function_datagrid(xrast, functions, xname, usingrowcol, using, select_criteria, select_cont, every, vars, plotwords['style'], verb_errors=verb_errors)

  # Tabulate a dataset
  for data_section in range(1,len(totalgrid)): # Loop over data sections within index, plotting each as a separate line 
   [rows, columns, datagrid] = totalgrid[data_section]
   if (data_section == 1): repeat = 0 # Are we to use same style as previous lump of data we plotted?
   else                  : repeat = 1
   return [tabulate_dataset(multiplot_number,axes,axis_x,axis_y,plotwords,settings,title,datagrid,rows,columns,"function '%s'"%function_str,repeat,verb_errors)]

# WITH_WORDS_CLEANUP(): Take a dictionary of style words, and clean up by: (i)
# Replacing colour numbers with colour names as necessary, and (ii)
# substituting for any linestyles found.

def with_words_cleanup(dict_in, style_default, settings, linestyles, vars, verb_errors):
 dict_out = dict_in.copy()

 for loop in [0, 1]: # A slightly unattractive way of doing a da capo aria in python...

   linestyle_depth = 0
   while 'linestyle' in dict_out:
    linestyle_depth += 1
    ls_number = dict_out['linestyle']
    del dict_out['linestyle']
    if (linestyle_depth > 5):
     if verb_errors: gp_error("Error: Linestyle iteration ceiling hit whilst processing linestyle %d."%ls_number)
    elif ls_number not in linestyles:
     if verb_errors: gp_error("Error: Linestyle %d not defined."%ls_number)
    else:
     for item in linestyles[ls_number].keys():
      if item not in dict_out:
       dict_out[item] = linestyles[ls_number][item]

   if (loop == 0):
     # Insert default style words; after we've done so, pick up any new linestyles which they contained with our little da capo coda
     for item in style_default.keys():
      if item not in dict_out:
       dict_out[item] = style_default[item]

 # Insert hard defaults
 if 'colour'         not in dict_out: dict_out['colour']         = "gp_auto"
 if 'fillcolour'     not in dict_out: dict_out['fillcolour']     = "gp_auto"
 if 'linetype'       not in dict_out: dict_out['linetype']       = -1
 if 'linewidth'      not in dict_out: dict_out['linewidth']      = settings['LINEWIDTH']
 if 'pointlinewidth' not in dict_out: dict_out['pointlinewidth'] = settings['POINTLINEWIDTH']
 if 'pointsize'      not in dict_out: dict_out['pointsize']      = settings['POINTSIZE']
 if 'pointtype'      not in dict_out: dict_out['pointtype']      = -1
 if 'style'          not in dict_out: dict_out['style']          = 'points'

 # Convert colour numbers into colour names
 for item in ['colour','fillcolour']:
  if (dict_out[item] == "gp_auto"):
   pass
  elif (dict_out[item].capitalize() in gp_settings.colours):
   dict_out[item] = dict_out[item].capitalize()
  else:
   try: 
    colnum = gp_eval.gp_eval(dict_out[item], vars, verbose=False)
    dict_out[item] = gp_settings.colour_list[(int(colnum)-1)%len(gp_settings.colour_list)]
   except KeyboardInterrupt: raise
   except:
    if verb_errors: gp_error("Expression '%s' was not recognised as a colour name, nor does it compute as a colour number:"%dict_out[item])
    dummy = gp_eval.gp_eval(dict_out[item], vars, verbose=False)

 return dict_out # Return cleaned up 'with' words

# TITLE_AUTOSTRING_GENERATE(): Generate the bit of the autotitle which comes after the datafile / function name

def title_autostring_generate(every,index,select_criteria,using):
 title = ""
 if every != []:
  title += "every "
  for i in range(len(every)):
   if i!=0: title += ":"
   if 'every_item' in every[i]: title += "%s"%every[i]['every_item']
  title += " "
 if index != -1:
  title += "index %s "%index
 if select_criteria != "":
  title += "select %s "%select_criteria
 if using != []:
  title += "using "
  for i in range(len(using)):
   if i!=0: title += ":"
   title += "%s"%using[i]
 return title

# TITLE_STRING_TEXIFY(): Convert illegal LaTeX characters into their command codes

def title_string_texify(title):
 title    = re.sub(r'[\\]', r'gpzywxqqq', title) # LaTeX does not like backslashs
 title    = re.sub(r'[_]', r'\\_', title) # LaTeX does not like underscores....
 title    = re.sub(r'[&]', r'\\&', title) # LaTeX does not like ampersands....
 title    = re.sub(r'[%]', r'\\%', title) # LaTeX does not like percents....
 title    = re.sub(r'[$]', r'\\$', title) # LaTeX does not like $s....
 title    = re.sub(r'[{]', r'\\{', title) # LaTeX does not like {s....
 title    = re.sub(r'[}]', r'\\}', title) # LaTeX does not like }s....
 title    = re.sub(r'[#]', r'\\#', title) # LaTeX does not like #s....
 title    = re.sub(r'[\^]', r'\\^{}', title) # LaTeX does not like carets....
 title    = re.sub(r'[~]', r'$\\sim$', title) # LaTeX does not like tildas....
 title = re.sub(r'[<]', r'$<$', title) # LaTeX does not like < outside of mathmode....
 title = re.sub(r'[>]', r'$>$', title) # LaTeX does not like > outside of mathmode....
 title    = re.sub(r'gpzywxqqq', r'$\\backslash$', title) # LaTeX does not like backslashs
 return title

# PLOT_LINEWIDTH(): Turn a numerical linewidth into a PyX style

def plot_linewidth(width):
  defaultlinewidth = 0.02 * unit.w_cm
  return style.linewidth(defaultlinewidth * width)

# TABULATE_DATASET(): Takes a request to plot a datafile/function and converts it into a list of datapoints and a PyX plot style

def tabulate_dataset(multiplot_number,axes,axis_x,axis_y,plotwords,settings,title,datagrid,rows,columns,description,repeat,verb_errors):
  global linecount, ptcount, colourcnt

  stylestr = plotwords['style']
  lw       = plot_linewidth(plotwords[     'linewidth'])
  plw      = plot_linewidth(plotwords['pointlinewidth'])

  # Check that we have a sufficient number of columns of data for this plot style
  columns_req = gp_settings.datastyleinfo[stylestr][1]
  if (columns < columns_req):
   if (verb_errors): gp_error("Need at least %d columns to plot data from %s."%(columns_req,description))
   return  

  if (columns > columns_req):
   if (verb_errors): gp_warning("Warning: Plot style '%s' requires only %d columns, but %d have been specified. Using the first %d."%(stylestr,columns_req,columns,columns_req))

  # If this is a histogram, then check whether it is a stacked barchart or not
  if stylestr in ['boxes', 'wboxes']:
    datagrid.sort(gp_math.sort_on_first_list_item)
    stacked_bars = [[]]
    prev_x       = None # x-coordinate of previous bar; used to test whether we're going to stack more on top of it
    prev_y       = None # Accumulator for adding up height of stacked bar in stacked barcharts
    prev_addons  = []   # Further columns after the height y
    i            = None # The stacking height of the current bar
    for datapoint in datagrid:
     if (datapoint[0] != prev_x): # We have a new x-coordinate, so start stacking a new stacked bar
      for j in range(len(stacked_bars)):
       while (len(stacked_bars[-1]) > len(stacked_bars[j])):
        stacked_bars[j].append([prev_x,prev_y]+prev_addons)
      i      = 0
      prev_x = datapoint[0]
      prev_y = 0.0
      prev_addons = datapoint[2:]
     else: # This point is at the same x-coordinate as previous point, so stack on top of it
      i += 1
     if (i >= len(stacked_bars)): stacked_bars.insert(0, stacked_bars[0][:-1]) # If we have a record stacking height, create a new barchart behind previous highest.
     prev_y += datapoint[1]
     prev_addons = datapoint[2:]
     stacked_bars[-1-i].append([prev_x,prev_y]+prev_addons)
    if (len(stacked_bars) > 1):
     for dataset in stacked_bars:
      return tabulate_dataset(multiplot_number,axes,axis_x,axis_y,plotwords,settings,title,dataset,len(dataset),columns,description,0,verb_errors)

  try:
    stylelist = []
    dx = None ; dxmin = None ; dxmax = None
    dy = None ; dymin = None ; dymax = None

    if (repeat == 1):
     localtitle = None    # Stops key have multiple references to the same line
    else:
     localtitle = title
     if ((localtitle != None) and (len(localtitle) < 1)): # Don't put blank titles into key
      localtitle = None

    # Determine what colour to use to plot this dataset

    if (gp_settings.settings_global['COLOUR'] == 'ON'): # Match colour
     if (plotwords['colour'] == "gp_auto"):
      if (repeat != 0): colourcnt  = colourcnt -1
      colour = gp_settings.pyx_colours[gp_settings.colour_list[(colourcnt-1)%len(gp_settings.colour_list)]] # If plot colour not set, automatically increment colour
      colourcnt  = colourcnt + 1
     else:
      colour = gp_settings.pyx_colours[plotwords['colour']] # otherwise used specified colour
    else:
      colour = color.grey.black # If monochrome, then set colour to black

    # Preplot action... if spline linestyle, then make a spline....
    if (stylestr in ['csplines','acsplines']):
      if (stylestr == 'csplines'): smoothing = 0.0
      else:                        smoothing = 1.0
      if (rows < 4) and verb_errors: gp_warning("Attempt to make spline doomed to fail -- need at least four data points to make a cubic spline.")
      try:
        [xmin, xmax, splineobj] = gp_spline.make_spline_object(rows,columns,datagrid,smoothing)
      except KeyboardInterrupt: raise
      except:
        raise "Failed to make spline object."
      datagrid  = []
      if (axes['x'][axis_x]['SETTINGS']['LOG'] == 'ON'): xrast = gp_math.lograst(xmin,xmax,settings['SAMPLES'])
      else:                                              xrast = gp_math.linrast(xmin,xmax,settings['SAMPLES'])
      for x in xrast: datagrid.append([x,gp_spline.spline_evaluate(x, splineobj)])

    # Now determine what linestyle to use, and make a list of style items to plot (in the case of linespoints or error bars, there are more than one)

    if (stylestr in ['lines','linespoints','csplines','acsplines']): # Match lines and linespoints
      if (plotwords['linetype'] < 0):
        if (gp_settings.settings_global['COLOUR'] == 'ON'):
          plotwords['linetype'] = 1 # Colour lines are automatically all solid
        else:
          if (repeat != 0): linecount = linecount - 1
          plotwords['linetype'] = linecount # Monochrome lines automatically have different linestyles
          linecount = linecount + 1
      stylelist.append(graph.style.line(lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour ]))
    if (stylestr in ['arrows_head','arrows_nohead','arrows_twohead']):
      if (plotwords['linetype'] < 0):
        if (gp_settings.settings_global['COLOUR'] == 'ON'):
          plotwords['linetype'] = 1 # Colour lines are automatically all solid
        else:
          if (repeat != 0): linecount = linecount - 1
          plotwords['linetype'] = linecount # Monochrome lines automatically have different linestyles
          linecount = linecount + 1
      if ( ((datagrid[0][0] == datagrid[1][0]) and (datagrid[0][1] == datagrid[1][1])) # arrow doesn't go anywhere, which is bad. Put no heads on such arrows.
          or (stylestr == 'arrows_nohead') ):
        stylelist.append(graph.style.line(lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour ]))
      elif (stylestr == 'arrows_head'):
        stylelist.append(graph.style.line(lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour , deco.earrow.normal]))
      else:
        stylelist.append(graph.style.line(lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour , deco.barrow.normal, deco.earrow.normal]))
    if (stylestr in ['points','linespoints']): # Match points and linespoints
      if (plotwords['pointtype'] < 0):
        if (repeat != 0): ptcount   = ptcount - 1
        plotwords['pointtype'] = ptcount # Both colour and monochrome point types automatically increment
        ptcount                = ptcount + 1
      for symboldata in gp_settings.symbol_list[(plotwords['pointtype']-1)%len(gp_settings.symbol_list)]:
        if symboldata[1]: fillattr = [deco.filled([colour])]
        else            : fillattr = []
        stylelist.append(graph.style.symbol(size=0.1*plotwords['pointsize'], symbol=symboldata[0], symbolattrs=[colour,plw]+fillattr))
    if (stylestr == 'dots'): # Match dots
      stylelist.append(graph.style.symbol(size=0.005*plotwords['pointsize'], symbol=graph.style.symbol.circle, symbolattrs=[colour,deco.filled([colour])]))
    if (stylestr in ['boxes', 'wboxes', 'impulses', 'steps', 'fsteps', 'histeps']): # Match boxes
      dx=3 # Widths of boxes are about to be put into a third column
      if (plotwords['linetype'] < 0):
        if (gp_settings.settings_global['COLOUR'] == 'ON'):
          plotwords['linetype'] = 1 # Colour lines are automatically all solid
        else:
          if (repeat != 0): linecount = linecount - 1
          plotwords['linetype'] = linecount # Monochrome lines automatically have different linestyles
          linecount = linecount + 1
      if (stylestr != 'wboxes'): # Work out widths of boxes
       datagrid_cpy      = []
       ptA = ptB = ptC = None
       for ptlist in datagrid:
        ptA = ptB ; ptB = ptC ; ptC = ptlist
        if (ptB != None):
         if (ptA != None): # Box in the midst of other boxes
          if (stylestr in ['boxes', 'histeps']):
           if (settings['BOXWIDTH'] <= 0.0)    : datagrid_cpy.append([ (ptB[0]+(ptA[0]+ptC[0])/2)/2 , ptB[1] , (ptC[0]-ptA[0])/4      ])
           else                                : datagrid_cpy.append([ ptB[0]                       , ptB[1] , settings['BOXWIDTH']/2 ])
          if (stylestr == 'impulses')          : datagrid_cpy.append([ ptB[0]                       , ptB[1] , 0.0                    ])
          if (stylestr == 'steps')             : datagrid_cpy.append([ (ptA[0]+ptB[0])/2            , ptB[1] , (ptB[0]-ptA[0])/2      ])
          if (stylestr == 'fsteps')            : datagrid_cpy.append([ (ptC[0]+ptB[0])/2            , ptB[1] , (ptC[0]-ptB[0])/2      ])
         else: # The first box we work out the width of
          if (stylestr in ['boxes', 'histeps']):
           if (settings['BOXWIDTH'] <= 0.0)    : datagrid_cpy.append([ ptB[0]                       , ptB[1] , (ptC[0]-ptB[0])/2      ])
           else                                : datagrid_cpy.append([ ptB[0]                       , ptB[1] , settings['BOXWIDTH']/2 ])
          if (stylestr == 'impulses')          : datagrid_cpy.append([ ptB[0]                       , ptB[1] , 0.0                    ])
          if (stylestr == 'steps')             : datagrid_cpy.append([ ptB[0]                       , ptB[1] , 0.0                    ])
          if (stylestr == 'fsteps')            : datagrid_cpy.append([ (ptC[0]+ptB[0])/2            , ptB[1] , (ptC[0]-ptB[0])/2      ])
       if (ptB != None): # The last box we work out the width of
          if (stylestr in ['boxes', 'histeps']):
           if (settings['BOXWIDTH'] <= 0.0)    : datagrid_cpy.append([ ptC[0]                       , ptC[1] , (ptC[0]-ptB[0])/2      ])
           else                                : datagrid_cpy.append([ ptC[0]                       , ptC[1] , settings['BOXWIDTH']/2 ])
          if (stylestr == 'impulses')          : datagrid_cpy.append([ ptC[0]                       , ptC[1] , 0.0                    ])
          if (stylestr == 'steps')             : datagrid_cpy.append([ (ptC[0]+ptB[0])/2            , ptC[1] , (ptC[0]-ptB[0])/2      ])
          if (stylestr == 'fsteps')            : datagrid_cpy.append([ ptC[0]                       , ptC[1] , 0.0                    ])
       else: # Special case for datasets with only one box
          if (stylestr in ['boxes', 'histeps', 'steps', 'fsteps']):
           if (settings['BOXWIDTH'] <= 0.0): datagrid_cpy.append([ ptC[0], ptC[1], 0.5                    ])
           else                            : datagrid_cpy.append([ ptC[0], ptC[1], settings['BOXWIDTH']/2 ])
          if (stylestr == 'impulses')          : datagrid_cpy.append([ ptC[0]                       , ptC[1] , 0.0                    ])
       datagrid = datagrid_cpy
      else: # Work out widths of wboxes
       datagrid_cpy      = []
       for pt in datagrid: datagrid_cpy.append([ pt[0], pt[1], 0.5*pt[2] ])
       datagrid = datagrid_cpy
      if   (stylestr in ['boxes', 'wboxes', 'impulses']):
       if (plotwords['fillcolour'] == "gp_auto"): # Process fill colour if we're going to fill our boxes
        fillcolset = None
       elif (gp_settings.settings_global['COLOUR'] != 'ON'):
        fillcolset = deco.filled([colour])
       elif (plotwords['fillcolour'] == "auto"): # Fill colour auto --> fill box with line colour
        fillcolset = deco.filled([colour])
       else:
        fillcolset = deco.filled([ gp_settings.pyx_colours[plotwords['fillcolour']] ])
       lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour ]
       if (fillcolset != None): lineattrs.extend([fillcolset])
       fromvalue = settings['BOXFROM']
       if (fromvalue < 0) and (axes['y'][axis_y]['SETTINGS']['LOG'] == 'ON'): fromvalue=1e-300 # On log axes, where if fromvalue is <= 0, badness happens
       stylelist.append(graph.style.histogram(lineattrs=lineattrs, steps=0, fillable=1, fromvalue=fromvalue))
      elif (stylestr in ['steps', 'fsteps', 'histeps']):
       datagrid_cpy      = []
       for pt in datagrid:
        datagrid_cpy.append([pt[0]-pt[2],pt[1]])
        datagrid_cpy.append([pt[0]+pt[2],pt[1]])
       datagrid = datagrid_cpy
       dx=None
       stylelist.append(graph.style.line(lineattrs=[ gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour ]))
    if (re.search('error',stylestr) != None): # Match {x|y|xy}error{bars|range}
      if (plotwords['linetype'] < 0):
        if (gp_settings.settings_global['COLOUR'] == 'ON'):
          plotwords['linetype'] = 1 # Colour errorbars are automatically all solid
        else:
          if (repeat != 0): linecount = linecount - 1
          plotwords['linetype'] = linecount
          linecount = linecount + 1
      stylelist.append(graph.style.errorbar(size=0.1*plotwords['pointsize']*settings['BAR'], errorbarattrs=[gp_settings.linestyle_list[(plotwords['linetype']-1)%len(gp_settings.linestyle_list)], lw, colour]))
      if (plotwords['pointtype'] < 0): stylelist.append(graph.style.symbol(size=0.1*plotwords['pointsize'], symbol=graph.style.symbol.plus, symbolattrs=[colour,lw]))
      else:
         for symboldata in gp_settings.symbol_list[(plotwords['pointtype']-1)%len(gp_settings.symbol_list)]:
          if symboldata[1]: fillattr = [deco.filled([colour])]
          else            : fillattr = []
          stylelist.append(graph.style.symbol(size=0.1*plotwords['pointsize'], symbol=symboldata[0], symbolattrs=[colour,plw]+fillattr))
      if   (stylestr == 'xerrorbars'  ): dx = 3
      elif (stylestr == 'yerrorbars'  ): dy = 3
      elif (stylestr == 'xyerrorbars' ): dx = 3 ; dy = 4
      elif (stylestr == 'xerrorrange' ): dxmin = 3 ; dxmax = 4
      elif (stylestr == 'yerrorrange' ): dymin = 3 ; dymax = 4
      elif (stylestr == 'xyerrorrange'): dxmin = 3 ; dxmax = 4 ; dymin = 5 ; dymax = 6

    # Clean up datagrid, removing any points < 0 which might go on log axis
    datagrid_cpy_list = []
    datagrid_cpy      = []
    for ptlist in datagrid:
      if (((axes['x'][axis_x]['SETTINGS']['LOG'] == 'ON') and (ptlist[0] <= 0.0)) or
          ((axes['y'][axis_y]['SETTINGS']['LOG'] == 'ON') and (ptlist[1] <= 0.0))):
       if (len(datagrid_cpy) != 0):
        datagrid_cpy_list.append(datagrid_cpy)
        datagrid_cpy = [] # Split dataset, not connecting points where it goes to minus infinity
      else:
       datagrid_cpy.append(ptlist)
    if (len(datagrid_cpy) != 0): datagrid_cpy_list.append(datagrid_cpy)
    if (len(datagrid_cpy_list) == 0): return # No data to plot!

    return {'datagrid_cpy_list':datagrid_cpy_list,
            'axes':axes,
            'axis_x':axis_x,
            'axis_y':axis_y,
            'dx':dx,
            'dxmin':dxmin,
            'dy':dy,
            'dymin':dymin,
            'localtitle':localtitle,
            'stylelist':stylelist,
            'stylestr':stylestr,
            'description':description,
            'verb_errors':verb_errors
            }

  except KeyboardInterrupt: raise
  except:
    if (verb_errors):
      gp_error("Failed while plotting %s:"%description)
      gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
      return # Error

# AXES_AUTOSCALE: Take the output from the above function and see if any autoscaling axes need extending to accommodate it

def axes_autoscale(multiplot_number,settings,datagrid_cpy_list,axes,axis_x,axis_y,localtitle,stylestr,description,verb_errors):
 global successful_plot_operations
 try:
  for datagrid_cpy in datagrid_cpy_list:
   if (localtitle != None): successful_plot_operations[multiplot_number] = 'ON' # Only count datasets which will put an entry into the key
   for i in range(len(datagrid_cpy)):
    # First time around, we recalculate data bounding box
    xaxis_min = gp_math.min( axes['x'][axis_x]['SETTINGS']['MIN'] , axes['x'][axis_x]['SETTINGS']['MAX'] )
    xaxis_max = gp_math.max( axes['x'][axis_x]['SETTINGS']['MIN'] , axes['x'][axis_x]['SETTINGS']['MAX'] )
    yaxis_min = gp_math.min( axes['y'][axis_y]['SETTINGS']['MIN'] , axes['y'][axis_y]['SETTINGS']['MAX'] )
    yaxis_max = gp_math.max( axes['y'][axis_y]['SETTINGS']['MIN'] , axes['y'][axis_y]['SETTINGS']['MAX'] )

    xpoints = [datagrid_cpy[i][0]]
    ypoints = [datagrid_cpy[i][1]]
    if   (stylestr == 'xerrorbars'  ): xpoints.extend([datagrid_cpy[i][0]-datagrid_cpy[i][2],datagrid_cpy[i][0]+datagrid_cpy[i][2]])
    elif (stylestr == 'yerrorbars'  ): ypoints.extend([datagrid_cpy[i][1]-datagrid_cpy[i][2],datagrid_cpy[i][1]+datagrid_cpy[i][2]])
    elif (stylestr == 'xerrorrange' ): xpoints.extend([datagrid_cpy[i][2]                   ,datagrid_cpy[i][3]                   ])
    elif (stylestr == 'yerrorrange' ): ypoints.extend([datagrid_cpy[i][2]                   ,datagrid_cpy[i][3]                   ])
    elif (stylestr == 'xyerrorbars' ):
                                       xpoints.extend([datagrid_cpy[i][0]-datagrid_cpy[i][2],datagrid_cpy[i][0]+datagrid_cpy[i][2]])
                                       ypoints.extend([datagrid_cpy[i][1]-datagrid_cpy[i][3],datagrid_cpy[i][1]+datagrid_cpy[i][3]])
    elif (stylestr == 'xyerrorrange'):
                                       xpoints.extend([datagrid_cpy[i][2]                   ,datagrid_cpy[i][3]                   ])
                                       ypoints.extend([datagrid_cpy[i][4]                   ,datagrid_cpy[i][5]                   ])
    elif (stylestr in ['wboxes', 'boxes', 'impulses']):
                                       xpoints.extend([datagrid_cpy[i][0]-datagrid_cpy[i][2],datagrid_cpy[i][0]+datagrid_cpy[i][2]])
                                       ypoints.extend([settings['BOXFROM']                                        ])

    # First the x-bounding-box
    # Is datapoint within range of y-axis? If not, don't use it to recalculate x-bounding-box
    if (((yaxis_min == None) or (ypoints[0] >= yaxis_min)) and
        ((yaxis_max == None) or (ypoints[0] <= yaxis_max))     ):
     for xpoint in xpoints:
      if ((axes['x'][axis_x]['SETTINGS']['LOG'] != 'ON') or (xpoint > 0)): # Don't count negative points on log axes
       if (axes['x'][axis_x]['SETTINGS']['MIN'] == None): # Only modify bounding boxes that we are autoscaling
        if ((axes['x'][axis_x]['MIN_USED'] == None) or (axes['x'][axis_x]['MIN_USED'] > xpoint)): axes['x'][axis_x]['MIN_USED'] = xpoint
       if (axes['x'][axis_x]['SETTINGS']['MAX'] == None): # Only modify bounding boxes that we are autoscaling
        if ((axes['x'][axis_x]['MAX_USED'] == None) or (axes['x'][axis_x]['MAX_USED'] < xpoint)): axes['x'][axis_x]['MAX_USED'] = xpoint

    # Second the y-bounding-box
    # Is datapoint within range of x-axis? If not, don't use it to recalculate y-bounding-box
    if (((xaxis_min == None) or (xpoints[0] >= xaxis_min)) and
        ((xaxis_max == None) or (xpoints[0] <= xaxis_max))     ):
     for ypoint in ypoints:
      if ((axes['y'][axis_y]['SETTINGS']['LOG'] != 'ON') or (ypoint > 0)): # Don't count negative points on log axes
       if (axes['y'][axis_y]['SETTINGS']['MIN'] == None): # Only modify bounding boxes that we are autoscaling
        if ((axes['y'][axis_y]['MIN_USED'] == None) or (axes['y'][axis_y]['MIN_USED'] > ypoint)): axes['y'][axis_y]['MIN_USED'] = ypoint
       if (axes['y'][axis_y]['SETTINGS']['MAX'] == None): # Only modify bounding boxes that we are autoscaling
        if ((axes['y'][axis_y]['MAX_USED'] == None) or (axes['y'][axis_y]['MAX_USED'] < ypoint)): axes['y'][axis_y]['MAX_USED'] = ypoint

 except KeyboardInterrupt: raise
 except:
  if (verb_errors):
   gp_error("Failed while plotting %s:"%description)
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return # Error
 return

# PLOT_DATASET(): Take a datagrid and a list of PyX plot styles and actually send it to PyX for plotting

def plot_dataset(g,datagrid_cpy_list,axes,axis_x,axis_y,dx,dxmin,dy,dymin,localtitle,stylelist,description,verb_errors):
 try:
  for datagrid_cpy in datagrid_cpy_list:
   x_axisname = axes['x'][axis_x]['LINKINFO']['AXISPYXNAME']
   y_axisname = axes['y'][axis_y]['LINKINFO']['AXISPYXNAME']
   x_set = x_axisname+"=1,"
   y_set = y_axisname+"=2,"
   if (dx != None): dx_set = "d"+x_axisname+"=dx,"
   else           : dx_set = ""
   if (dy != None): dy_set = "d"+y_axisname+"=dy,"
   else           : dy_set = ""
   if (dxmin != None): dx_set = x_axisname+"min=dxmin,"+x_axisname+"max=dxmax,"
   if (dymin != None): dy_set = y_axisname+"min=dymin,"+y_axisname+"max=dymax,"
   exec "g.plot(graph.data.points(datagrid_cpy,"+x_set+y_set+dx_set+dy_set+"title=localtitle),styles=stylelist)"
   localtitle = None # Only put a title on one dataset
 except KeyboardInterrupt: raise
 except:
  if (verb_errors):
   gp_error("Failed while plotting %s:"%description)
   gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
   return # Error
 return

# WRITE_OUTPUT(): Moves output from file "infile" to file "outfile", possibly backing up any file which might be over-written

def write_output(infile, outfile, settings):
 if( gp_settings.settings_global['BACKUP']=="ON") and os.path.exists(outfile):
  i=0
  while os.path.exists("%s~%d"%(outfile,i)): i+=1
  os.rename(outfile,"%s~%d"%(outfile,i))
 outs = open(outfile,"wb")
 ins  = open(infile,"rb")
 dat  = "x"
 while dat!="":
  dat = ins.read(1024)
  outs.write(dat)
 outs.close
 ins.close()

# PYX_TEXTER_CLEANUP(): When PyX encounters a LaTeX problem, the text module tends to stop working. This code kicks it back into behaving again

def pyx_texter_cleanup():
 newtexter = text.texrunner()
 pyx_texrunner_init(newtexter)
 text.defaulttexrunner = newtexter
 text.reset    = newtexter.reset
 text.set      = newtexter.set
 text.preamble = newtexter.preamble
 text.text     = newtexter.text
 text.text_pt  = newtexter.text_pt

def pyx_texrunner_init(texter):
 texter.set(mode="latex",waitfortex=20)
 texter.preamble(gp_settings.latex_preamble)
