# GP_POSTSCRIPT.PY
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

# Contains routine for turning PyX's eps output into postscript
# This also involves knowing all about paper sizes

import os
import re
import sys
from math import *

# Paper sizes
# See http://www.cl.cam.ac.uk/~mgk25/iso-paper.html

# First of all, the difficult paper sizes
papersizes = {"quarto"                    :[ 254, 203],
              "foolscap"                  :[ 330, 203],
              "executive"                 :[ 267, 184],
              "monarch"                   :[ 267, 184],
              "government_letter"         :[ 267, 203],
              "letter"                    :[ 279, 216],
              "legal"                     :[ 356, 216],
              "ledger"                    :[ 432, 279],
              "tabloid"                   :[ 432, 279],
              "post"                      :[ 489, 394],
              "crown"                     :[ 508, 381],
              "large_post"                :[ 533, 419],
              "demy"                      :[ 572, 445],
              "medium"                    :[ 584, 457],
              "royal"                     :[ 635, 508],
              "elephant"                  :[ 711, 584],
              "double_demy"               :[ 889, 597],
              "quad_demy"                 :[1143, 889],
              "statement"                 :[ 216, 140],
              "international_businesscard":[85.60, 53.98],
              "us_businesscard"           :[  89,  51],
              "japanese_shiroku4"         :[ 379, 264],
              "japanese_shiroku5"         :[ 262, 189],
              "japanese_shiroku6"         :[ 188, 127],
              "japanese_kiku4"            :[ 306, 227],
              "japanese_kiku5"            :[ 227, 151],
              "envelope_dl"               :[ 110, 220], # Wider than it is long
              }

# Now the ISO series
papersizes['4a0'] = [int(sqrt(2)*sqrt(4e6/sqrt(2))), int(sqrt(4e6/sqrt(2)))] # 4A0 has area four square metres

height = sqrt(2)*sqrt(2e6/sqrt(2))
width  = sqrt(2e6/sqrt(2))
papersizes['2a0'] = [int(height), int(width)] # 2A0 has area two square metres

for size in range(11):
  new_height = height/sqrt(2)
  new_width  = width/sqrt(2)
  papersizes['japanese_b'+str(size)] = [int((new_height+height)/2), int((new_width+width)/2)]
  height = new_height ; width = new_width
  types = ['a', 'swedish_e', 'c', 'swedish_g', 'b', 'swedish_f', 'swedish_d', 'swedish_h']
  for type_n in range(len(types)):
    papersizes[types[type_n]+str(size)] = [int(height*(2.0**(float(type_n)/16))),int(width*(2.0**(float(type_n)/16)))]

# DEBUGGING CODE TO OUTPUT LIST OF RECOGNISED PAPERSIZES
# list = papersizes.items()
# list.sort()
# for type,size in list:
#  print "%27s %8.2f %8.2f"%(type,size[0],size[1])

mm_to_ps = 72 / 25.4 # Convert mm to postscript 72th of an inch
margins = {'LEFT':15, 'RIGHT':15, 'TOP':15, 'BOTTOM':30}

# GET_PAPERNAME(): a.k.a What do you call a piece of paper with these dimensions?

def get_papername(height, width):
  for size,[h,w] in papersizes.items():
    if (abs(h-height)<2) and (abs(w-width)<2):
      return size
  return "User-defined size"

# LANDSCAPE(): Converts a portrait eps file to landscape eps.  Output file has
# same filename as input file.

def landscape(filename):
  # Read the bounding box of the input eps file
  inbbox = getbbox(filename)

  # Calculate quantities necessary to generate the new postscript
  width = inbbox[2] - inbbox[0]
  height = inbbox[3] - inbbox[1]
  trans_x = -inbbox[2]
  trans_y = - inbbox[1]

  # New bounding box and geometric transformation
  newbbox = "%%%%BoundingBox: 0 0 %s %s\n"%(height,width)
  transformation = "-90 rotate\n%s %s translate\n"%(trans_x,trans_y)

  # Write the new postscript out
  infile = open(filename, "r")
  outfile = open("%s2"%filename, "w")

  # First wait for the bounding box, and when it turns up replace it
  for line in infile:
   test = re.match(r"%%BoundingBox: ",line)
   if (test != None):
    outfile.write(newbbox)
    break
   outfile.write(line)

   # Now do the same, waiting for the beginning of the eps proper
  for line in infile:
   outfile.write(line)
   test = re.match(r"%%EndProlog",line)
   if (test != None):
    outfile.write(transformation)
    break

  # And dump the rest of the postscript to the file
  for line in infile:
   outfile.write(line)
  
  os.system("mv %s2 %s"%(filename,filename))

# GETBBOX(): Gets the bounding box from a postscript file, returning it as
# [left, bottom, right, top]

def getbbox(filename):
  infile = open(filename,"r")
  inbbox = None
  for line in infile:
   test = re.match(r"%%BoundingBox:\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)",line)
   if (test != None):
    inbbox = [float(test.group(1)),float(test.group(2)),float(test.group(3)),float(test.group(4))]
    break
  infile.close()
  assert (inbbox != None), "Could not read bbox of PyX output"
  return inbbox
  
# ENLARGE(): Enlarges an eps file to fit the page.  Output file has same name
# as input file

def enlarge(filename, settings):
  # Read bounding box of the input eps file
  inbbox = getbbox(filename)
  width  = inbbox[2] - inbbox[0]
  height = inbbox[3] - inbbox[1]
  # Calculate the scaling in the x and y directions to see which is smallest
  xscaling = (settings['PAPER_WIDTH'] - margins['LEFT'] - margins['RIGHT'])*mm_to_ps/width
  yscaling = (settings['PAPER_HEIGHT'] - margins['TOP'] - margins['BOTTOM'])*mm_to_ps/height
  scaling = min(xscaling, yscaling)
  # Generate a line of postscript to transform the eps and a new bounding box
  xtrans = margins['LEFT'] * mm_to_ps - inbbox[0] * scaling
  ytrans = settings['PAPER_HEIGHT']*mm_to_ps - margins['TOP'] * mm_to_ps - inbbox[3]*scaling
  transformation = "%s %s translate\n%s %s scale\n"%(xtrans,ytrans,scaling,scaling)
  bbox = [0,0,0,0]
  bbox[0] = margins['LEFT']*mm_to_ps
  bbox[1] = (settings['PAPER_HEIGHT']-margins['TOP'])*mm_to_ps - height*scaling
  bbox[2] = margins['LEFT']*mm_to_ps + width*scaling
  bbox[3] = (settings['PAPER_HEIGHT']-margins['TOP'])*mm_to_ps
  newbbox = "%%%%BoundingBox: %s %s %s %s\n"%(bbox[0],bbox[1],bbox[2],bbox[3])

  # Write the new file out
  infile = open(filename, "r")
  outfile = open("%s2"%filename, "w")
  for line in infile:
   test = re.match(r"%%BoundingBox: ", line)
   if (test != None):
    outfile.write(newbbox)
    break
   outfile.write(line)

  for line in infile:
   outfile.write(line)
   test = re.match(r"%%EndProlog", line)
   if (test != None):
    outfile.write(transformation)
    break

  for line in infile:
   outfile.write(line)

  os.system("mv %s2 %s"%(filename, filename))

# EPSSETNAME(): Sets the title of an eps file. Output file has same filename as
# input file.

def epssetname(filename, title):
  # Write the new postscript out
  infile = open(filename, "r")
  outfile = open("%s2"%filename, "w")

  # Wait for the title, and when it turns up replace it
  for line in infile:
   test = re.match(r"%%Title: ",line)
   if (test != None):
    outfile.write("%%%%Title: %s\n"%title)
    break
   outfile.write(line)
  # Then write the rest of the file out
  for line in infile:
   outfile.write(line)

  infile.close()
  outfile.close()
  os.system("mv %s2 %s"%(filename,filename))

# EPSTOPS(): Converts EPS file to PS file. Output file has same filename as
# input file.

def epstops(filename, settings):
  # Read the bounding box of the input EPS file
  infile = open(filename,"r")
  inbbox = None
  for line in infile:
   test = re.match(r"%%BoundingBox:\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)",line)
   if (test != None):
    inbbox = [float(test.group(1)),float(test.group(2)),float(test.group(3)),float(test.group(4))]
    break
  infile.close()
  assert (inbbox != None), "Could not read bbox of PyX output"
 
  # Generate translation operation
  margin_x = 15 * mm_to_ps
  margin_y = margin_x
 
  trans_x = margin_x - inbbox[0] # Left margin - left bbox
  trans_y = settings['PAPER_HEIGHT'] * mm_to_ps - margin_y - inbbox[3]
 
  # Start producing output postscript
  outfile = open("%s2"%filename,"w")
  outfile.write("%%!PS-Adobe-2.0\n%%%%DocumentPaperSizes: %s\n"%settings['PAPER_NAME'])
  # The following line is bollocks, but it may be helpful bollocks in some circumstances
  outfile.write("%%%%BoundingBox: 0 0 %s %s\n"%(settings['PAPER_WIDTH']*mm_to_ps,settings['PAPER_HEIGHT']*mm_to_ps))
  outfile.write(r"""%%EndComments
/BeginEPSF { %def
  /b4_Inc_state save def                       % Save state for cleanup
  /dict_count countdictstack def               % Count objects on dict stack
  /op_count count 1 sub def                    % Count objects on operand stack
  userdict begin                               % Push userdict on dict stack
  /showpage { } def                            % Redefine showpage, { } = null proc
  0 setgray 0 setlinecap                       % Prepare graphics state
  1 setlinewidth 0 setlinejoin
  10 setmiterlimit [ ] 0 setdash newpath
  /languagelevel where                         % If level not equal to 1 then
  {pop languagelevel                           % set strokeadjust and
  1 ne                                         % overprint to their defaults.
     {false setstrokeadjust false setoverprint
     } if
  } if
} bind def
/EndEPSF { %def
  count op_count sub {pop} repeat       % Clean up stacks
  countdictstack dict_count sub {end} repeat
  b4_Inc_state restore
} bind def

BeginEPSF
""")
  outfile.write("%s %s translate\n"%(trans_x,trans_y))
  outfile.write("%%BeginDocument PyXPlotOutput\n")
 
  infile = open(filename,"r")
  for line in infile:
   outfile.write(line)
  infile.close()
 
  outfile.write("""
%%EndDocument
EndEPSF
showpage
""")

  os.system("mv %s2 %s"%(filename,filename))
