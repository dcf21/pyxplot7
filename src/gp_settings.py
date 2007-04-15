# GP_SETTINGS.PY
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

import os
import sys
import glob
import stat
import ConfigParser
import pyx

import gp_eval
import gp_postscript
from gp_error import *

#
# DEFAULT LINESTYLES AND POINTSTYLES
#

from gp_symbollist import symbol_list

linestyle_list = [pyx.style.linestyle.solid, pyx.style.linestyle.dashed, pyx.style.linestyle.dotted, pyx.style.linestyle.dashdotted, pyx.style.dash((3,2,1,1,1,2),0), pyx.style.dash((3,1,1,3,1,1),0), pyx.style.dash((3,1,3,1,3,1),0), pyx.style.dash((4,4),0)]

#
# CONFIGURATION FILE HANDLING
#

# Check for settings in configuration files .pyxplotrc in c.w.d. or user's homespace
config_list = [os.path.expanduser("~/.pyxplotrc"), ".pyxplotrc"]

try:
 config_files = ConfigParser.ConfigParser()
 config_files.read(config_list)
except KeyboardInterrupt: raise
except:
 config_files = None
 gp_warning("Warning: Could not parse configuration file -- missing section heading, perhaps?")

# CONFIG_LOOKUP_FOO(): Check for entry [section,option] in configuration file.
# If not found, return default.

def config_lookup_str(section, option, default):
 try   : return config_files.get(section, option)
 except KeyboardInterrupt: raise
 except: return default

def config_lookup_float(section, option, default):
 try   : value = config_files.get(section, option)
 except KeyboardInterrupt: raise
 except: return default
 try   : return float(value)
 except KeyboardInterrupt: raise
 except:
  gp_warning("Warning: Value '%s' for [%s,%s] in configuration file should be floating point."%(value, section, option))
  return default

def config_lookup_int(section, option, default, min=None):
 try   :
   value = config_files.get(section, option)
   assert value>=min, "Error: Configuration file value for setting [%s,%s] must be >= %s."%(section, option, value)
 except KeyboardInterrupt: raise
 except: return default
 try   : return int(value)
 except KeyboardInterrupt: raise
 except:
  gp_warning("Warning: Value '%s' for [%s,%s] in configuration file should be an integer."%(value, section, option))
  return default

def config_lookup_opt(section, option, default, options):
 try   : value = config_files.get(section, option)
 except KeyboardInterrupt: raise
 except: return default
 if (value in options): return value
 else:
  gp_warning("Warning: Value '%s' for [%s,%s] in configuration file should be one of options %s."%(value, section, option, options))
  return default

def config_lookup_opt2(section, option, default, options): # As above, but capitalises input
 try   : value = config_files.get(section, option)
 except KeyboardInterrupt: raise
 except: return default
 if (value.capitalize() in options): return value.capitalize()
 else:
  gp_warning("Warning: Value '%s' for [%s,%s] in configuration file should be one of options %s."%(value, section, option, options))
  return default

# Make a dictionary of PyX colours called pyx_colours

pyx_colours={
"Greenyellow":pyx.color.cmyk.GreenYellow,
"Yellow":pyx.color.cmyk.Yellow,
"Goldenrod":pyx.color.cmyk.Goldenrod,
"Dandelion":pyx.color.cmyk.Dandelion,
"Apricot":pyx.color.cmyk.Apricot,
"Peach":pyx.color.cmyk.Peach,
"Melon":pyx.color.cmyk.Melon,
"Yelloworange":pyx.color.cmyk.YellowOrange,
"Orange":pyx.color.cmyk.Orange,
"Burntorange":pyx.color.cmyk.BurntOrange,
"Bittersweet":pyx.color.cmyk.Bittersweet,
"Redorange":pyx.color.cmyk.RedOrange,
"Mahogany":pyx.color.cmyk.Mahogany,
"Maroon":pyx.color.cmyk.Maroon,
"Brickred":pyx.color.cmyk.BrickRed,
"Red":pyx.color.cmyk.Red,
"Orangered":pyx.color.cmyk.OrangeRed,
"Rubinered":pyx.color.cmyk.RubineRed,
"Wildstrawberry":pyx.color.cmyk.WildStrawberry,
"Salmon":pyx.color.cmyk.Salmon,
"Carnationpink":pyx.color.cmyk.CarnationPink,
"Magenta":pyx.color.cmyk.Magenta,
"Violetred":pyx.color.cmyk.VioletRed,
"Rhodamine":pyx.color.cmyk.Rhodamine,
"Mulberry":pyx.color.cmyk.Mulberry,
"Redviolet":pyx.color.cmyk.RedViolet,
"Fuchsia":pyx.color.cmyk.Fuchsia,
"Lavender":pyx.color.cmyk.Lavender,
"Thistle":pyx.color.cmyk.Thistle,
"Orchid":pyx.color.cmyk.Orchid,
"Darkorchid":pyx.color.cmyk.DarkOrchid,
"Purple":pyx.color.cmyk.Purple,
"Plum":pyx.color.cmyk.Plum,
"Violet":pyx.color.cmyk.Violet,
"Royalpurple":pyx.color.cmyk.RoyalPurple,
"Blueviolet":pyx.color.cmyk.BlueViolet,
"Periwinkle":pyx.color.cmyk.Periwinkle,
"Cadetblue":pyx.color.cmyk.CadetBlue,
"Cornflowerblue":pyx.color.cmyk.CornflowerBlue,
"Midnightblue":pyx.color.cmyk.MidnightBlue,
"Navyblue":pyx.color.cmyk.NavyBlue,
"Royalblue":pyx.color.cmyk.RoyalBlue,
"Blue":pyx.color.cmyk.Blue,
"Cerulean":pyx.color.cmyk.Cerulean,
"Cyan":pyx.color.cmyk.Cyan,
"Processblue":pyx.color.cmyk.ProcessBlue,
"Skyblue":pyx.color.cmyk.SkyBlue,
"Turquoise":pyx.color.cmyk.Turquoise,
"Tealblue":pyx.color.cmyk.TealBlue,
"Aquamarine":pyx.color.cmyk.Aquamarine,
"Bluegreen":pyx.color.cmyk.BlueGreen,
"Emerald":pyx.color.cmyk.Emerald,
"Junglegreen":pyx.color.cmyk.JungleGreen,
"Seagreen":pyx.color.cmyk.SeaGreen,
"Green":pyx.color.cmyk.Green,
"Forestgreen":pyx.color.cmyk.ForestGreen,
"Pinegreen":pyx.color.cmyk.PineGreen,
"Limegreen":pyx.color.cmyk.LimeGreen,
"Yellowgreen":pyx.color.cmyk.YellowGreen,
"Springgreen":pyx.color.cmyk.SpringGreen,
"Olivegreen":pyx.color.cmyk.OliveGreen,
"Rawsienna":pyx.color.cmyk.RawSienna,
"Sepia":pyx.color.cmyk.Sepia,
"Brown":pyx.color.cmyk.Brown,
"Tan":pyx.color.cmyk.Tan,
"Gray":pyx.color.cmyk.Gray,
"Grey":pyx.color.cmyk.Grey,
"Black":pyx.color.cmyk.Black,
"White":pyx.color.cmyk.White,
"Grey05":pyx.color.gray(0.05),
"Grey10":pyx.color.gray(0.10),
"Grey15":pyx.color.gray(0.15),
"Grey20":pyx.color.gray(0.20),
"Grey25":pyx.color.gray(0.25),
"Grey30":pyx.color.gray(0.30),
"Grey35":pyx.color.gray(0.35),
"Grey40":pyx.color.gray(0.40),
"Grey45":pyx.color.gray(0.45),
"Grey50":pyx.color.gray(0.50),
"Grey55":pyx.color.gray(0.55),
"Grey60":pyx.color.gray(0.60),
"Grey65":pyx.color.gray(0.65),
"Grey70":pyx.color.gray(0.70),
"Grey75":pyx.color.gray(0.75),
"Grey80":pyx.color.gray(0.80),
"Grey85":pyx.color.gray(0.85),
"Grey90":pyx.color.gray(0.90),
"Grey95":pyx.color.gray(0.95),
"Gray05":pyx.color.gray(0.05),
"Gray10":pyx.color.gray(0.10),
"Gray15":pyx.color.gray(0.15),
"Gray20":pyx.color.gray(0.20),
"Gray25":pyx.color.gray(0.25),
"Gray30":pyx.color.gray(0.30),
"Gray35":pyx.color.gray(0.35),
"Gray40":pyx.color.gray(0.40),
"Gray45":pyx.color.gray(0.45),
"Gray50":pyx.color.gray(0.50),
"Gray55":pyx.color.gray(0.55),
"Gray60":pyx.color.gray(0.60),
"Gray65":pyx.color.gray(0.65),
"Gray70":pyx.color.gray(0.70),
"Gray75":pyx.color.gray(0.75),
"Gray80":pyx.color.gray(0.80),
"Gray85":pyx.color.gray(0.85),
"Gray90":pyx.color.gray(0.90),
"Gray95":pyx.color.gray(0.95)
}

# Available options for different data types

datastyleinfo = {'points'         : ['1:2',         2,2],
                 'lines'          : ['1:2',         2,2],
                 'linespoints'    : ['1:2',         2,2],
                 'xerrorbars'     : ['1:2:3',       3,2],
                 'yerrorbars'     : ['1:2:3',       3,2],
                 'xyerrorbars'    : ['1:2:3:4',     4,2],
                 'xerrorrange'    : ['1:2:3:4',     4,2],
                 'yerrorrange'    : ['1:2:3:4',     4,2],
                 'xyerrorrange'   : ['1:2:3:4:5:6', 6,2],
                 'dots'           : ['1:2',         2,2],
                 'impulses'       : ['1:2',         2,2],
                 'boxes'          : ['1:2',         2,2],
                 'wboxes'         : ['1:2:3',       3,2],
                 'steps'          : ['1:2',         2,2],
                 'fsteps'         : ['1:2',         2,2],
                 'histeps'        : ['1:2',         2,2],
                 'arrows_head'    : ['1:2:3:4',     4,5],
                 'arrows_nohead'  : ['1:2:3:4',     4,5],
                 'arrows_twohead' : ['1:2:3:4',     4,5],
                 'csplines'       : ['1:2',         2,2],
                 'acsplines'      : ['1:2',         2,2],
                 'tabulate'       : ['1:2',         2,None]  # tabulate does not consider error bars
                 }

# Recognised positions for plot keys

key_positions = {
                 "TOP RIGHT":     [1.0, 1.0 , 1, 1],
                 "TOP MIDDLE":    [0.5, 1.0 , 1, 1],
                 "TOP LEFT":      [0.0, 1.0 , 1, 1],
                 "MIDDLE RIGHT":  [1.0, 0.5 , 1, 1],
                 "MIDDLE MIDDLE": [0.5, 0.5 , 1, 1],
                 "MIDDLE LEFT":   [0.0, 0.5 , 1, 1],
                 "BOTTOM RIGHT":  [1.0, 0.0 , 1, 1],
                 "BOTTOM MIDDLE": [0.5, 0.0 , 1, 1],
                 "BOTTOM LEFT":   [0.0, 0.0 , 1, 1],
                 "BELOW":         [0.5, 0.0 , 1, 0],
                 "OUTSIDE":       [1.0, 1.0 , 0, 1]
                 }


datastyles = ['points','lines','linespoints','xerrorbars','yerrorbars','xyerrorbars','xerrorrange','yerrorrange','xyerrorrange','dots','impulses','boxes','wboxes','steps','fsteps','histeps','arrows_head','arrows_nohead','arrows_twohead','csplines','acsplines']
onoff      = ['ON', 'OFF']
termtypes  = ['X11_singlewindow','X11_multiwindow','X11_persist','PS','EPS','PDF','PNG','JPG','GIF']
keyposes   = ["TOP RIGHT","TOP MIDDLE","TOP LEFT","MIDDLE RIGHT","MIDDLE MIDDLE","MIDDLE LEFT","BOTTOM RIGHT","BOTTOM MIDDLE","BOTTOM LEFT","BELOW","OUTSIDE"]
ticdirs    = ['INWARD', 'OUTWARD', 'BOTH']
halignment = ['Left','Centre','Right']
valignment = ['Top','Centre','Bottom']
fontsizes  = ['-4', '-3', '-2', '-1', '0', '1', '2', '3', '4', '5']
colours    = pyx_colours.keys()

#
# DEFAULT PALETTE
#

colour_list_default = ['Black', 'Red', 'Blue', 'Magenta', 'Cyan', 'Brown', 'Salmon', 'Gray', 'Green', 'Navyblue', 'Periwinkle', 'Pinegreen', 'Seagreen', 'Greenyellow', 'Orange', 'Carnationpink', 'Plum' ]

# Now set default options, using configuration file settings as overide if present

settings_default = {
                    'AXESCOLOUR'     :config_lookup_opt2 ('settings','AXESCOLOUR'     ,'Black'           ,colours   ) ,
                    'ASPECT'         :config_lookup_float('settings','ASPECT'         ,1.0                          ) , # Aspect ratio of plot
                    'AUTOASPECT'     :config_lookup_opt  ('settings','AUTOASPECT'     ,'ON'              ,onoff     ) , # Use PyX default aspect ratio
                    'BACKUP'         :config_lookup_opt  ('settings','BACKUP'         ,'OFF'             ,onoff     ) ,
                    'BAR'            :config_lookup_float('settings','BAR'            ,1.0                          ) ,
                    'BINORIGIN'      :config_lookup_float('settings','BINORIGIN'      ,0.0                          ) ,
                    'BINWIDTH'       :config_lookup_float('settings','BINWIDTH'       ,1.0                          ) ,
                    'BOXFROM'        :config_lookup_float('settings','BOXFROM'        ,0.0                          ) ,
                    'BOXWIDTH'       :config_lookup_float('settings','BOXWIDTH'       ,0.0                          ) ,
                    'COLOUR'         :config_lookup_opt  ('settings','COLOUR'         ,'ON'              ,onoff     ) ,
                    'DATASTYLE'      :config_lookup_opt  ('settings','DATASTYLE'      ,'points'          ,datastyles) ,
                    'DISPLAY'        :config_lookup_opt  ('settings','DISPLAY'        ,'ON'              ,onoff     ) ,
                    'DPI'            :config_lookup_float('settings','DPI'            ,300.0                        ) , # DPI of bitmap graphics output.
                    'FONTSIZE'       :int(config_lookup_opt('settings','FONTSIZE'     ,'0'               ,fontsizes )), # Font size (-4 < i < 5)
                    'FUNCSTYLE'      :config_lookup_opt  ('settings','FUNCSTYLE'      ,'lines'           ,datastyles) ,
                    'GRID'           :config_lookup_opt  ('settings','GRID'           ,'OFF'             ,onoff     ) ,
                    'GRIDAXISX'      :[config_lookup_int ('settings','GRIDAXISX'      ,1                            ) ], # List of axes which grid attaches to
                    'GRIDAXISY'      :[config_lookup_int ('settings','GRIDAXISY'      ,1                            ) ],
                    'GRIDMAJCOLOUR'  :config_lookup_opt2 ('settings','GRIDMAJCOLOUR'  ,'Grey60'          ,colours   ) ,
                    'GRIDMINCOLOUR'  :config_lookup_opt2 ('settings','GRIDMINCOLOUR'  ,'Grey90'          ,colours   ) ,
                    'KEY'            :config_lookup_opt  ('settings','KEY'            ,'ON'              ,onoff     ) ,
                    'KEYCOLUMNS'     :config_lookup_int  ('settings','KEYCOLUMNS'     ,1                 ,min=1     ) ,
                    'KEYPOS'         :config_lookup_opt  ('settings','KEYPOS'         ,'TOP RIGHT'       ,keyposes  ) , # Text description of key pos
                    'KEY_XOFF'       :config_lookup_float('settings','KEY_XOFF'       ,0.0                          ) ,
                    'KEY_YOFF'       :config_lookup_float('settings','KEY_YOFF'       ,0.0                          ) ,
                    'LANDSCAPE'      :config_lookup_opt  ('settings','LANDSCAPE'      ,'OFF'             ,onoff     ) , # Landscape output?
                    'LINEWIDTH'      :config_lookup_float('settings','LINEWIDTH'      ,1.0                          ) , # Default linewidth
                    'MULTIPLOT'      :config_lookup_opt  ('settings','MULTIPLOT'      ,'OFF'             ,onoff     ) ,
                    'ORIGINX'        :config_lookup_float('settings','ORIGINX'        ,0.0                          ) ,
                    'ORIGINY'        :config_lookup_float('settings','ORIGINY'        ,0.0                          ) ,
                    'OUTPUT'         :config_lookup_str  ('settings','OUTPUT'         ,''                           ) ,
                    'POINTSIZE'      :config_lookup_float('settings','POINTSIZE'      ,1.0                          ) , # Default pointsize
                    'POINTLINEWIDTH' :config_lookup_float('settings','POINTLINEWIDTH' ,1.0             ) , # Default linewidth used for drawing points
                    'SAMPLES'        :config_lookup_int  ('settings','SAMPLES'        ,250               ,min=1     ) ,
                    'TERMTYPE'       :config_lookup_opt  ('settings','TERMTYPE'       ,'X11_singlewindow',termtypes ) ,
                    'TEXTCOLOUR'     :config_lookup_opt2 ('settings','TEXTCOLOUR'     ,'Black'           ,colours   ) ,
                    'TERMENLARGE'    :config_lookup_opt  ('settings','ENLARGE'        ,'OFF'             ,onoff     ) , # Does terminal enlarge output?
                    'TEXTHALIGN'     :config_lookup_opt2 ('settings','TEXTHALIGN'     ,'Left'            ,halignment) ,
                    'TEXTVALIGN'     :config_lookup_opt2 ('settings','TEXTVALIGN'     ,'Bottom'          ,valignment) ,
                    'TITLE'          :config_lookup_str  ('settings','TITLE'          ,''                           ) , # Plot title
                    'TIT_XOFF'       :config_lookup_float('settings','TIT_XOFF'       ,0.0                          ) , # x offset of title
                    'TIT_YOFF'       :config_lookup_float('settings','TIT_YOFF'       ,0.0                          ) , # bitmap terminals produce inv output?
                    'TERMINVERT'     :config_lookup_opt  ('settings','TERMINVERT'     ,'OFF'             ,onoff     ) , # Inverted colour image output?
                    'TERMTRANSPARENT':config_lookup_opt  ('settings','TERMTRANSPARENT','OFF'             ,onoff     ) , # Image output transparent?
                    'WIDTH'          :config_lookup_float('settings','WIDTH'          ,8.0                          ) , # Width of output / cm
                    }

settings_default['DATASTYLE'] = {'style':settings_default['DATASTYLE']}
settings_default['FUNCSTYLE'] = {'style':settings_default['FUNCSTYLE']}

try:
  get_papersize = os.popen("locale -c LC_PAPER 2> /dev/null") # Read locale papersize
  get_papersize.readline()
  settings_default['PAPER_HEIGHT'] = float(get_papersize.readline())
  settings_default['PAPER_WIDTH']  = float(get_papersize.readline())
  get_papersize.close()
  assert settings_default['PAPER_HEIGHT'] > 0
  assert settings_default['PAPER_WIDTH']  > 0
except:
  settings_default['PAPER_HEIGHT'] = 297 # If can't read the default locale papersize, use A4 instead
  settings_default['PAPER_WIDTH']  = 210

settings_default['PAPER_HEIGHT'] = config_lookup_float('settings','PAPER_HEIGHT',settings_default['PAPER_HEIGHT']) # Config file can override this, though
settings_default['PAPER_WIDTH']  = config_lookup_float('settings','PAPER_WIDTH' ,settings_default['PAPER_WIDTH' ])
settings_default['PAPER_NAME']   = gp_postscript.get_papername(settings_default['PAPER_HEIGHT'], settings_default['PAPER_WIDTH'])

default_axis = {'LABEL'    : '', # These are the axis settings which the unset command accesses
                'MIN'      : None,
                'MAX'      : None,
                'LOG'      : 'OFF',
                'LOGBASE'  : 10.0,
                'TICDIR'   : config_lookup_opt('settings','TICDIR','INWARD',ticdirs),
                'TICKLIST' : None,
                'TICKMIN'  : None,
                'TICKSTEP' : None,
                'TICKMAX'  : None,
                'MTICKLIST' : None,
                'MTICKMIN'  : None,
                'MTICKSTEP' : None,
                'MTICKMAX'  : None
                }

default_new_axis = default_axis.copy() # This is the prototype of a new axis. It is modified by, e.g. set notics, acting on all axes.

linestyles = {} # User-defined linestyles
arrows     = {} # Arrows superposed on figure
labels     = {} # Text labels

variables  = {'pi':3.14159265358979} # User-defined variables
functions  = {}                      # User-defined functions

# NOW IMPORT FUNCTIONS FROM CONFIGURATION FILE

try:
 for preconfigvar in config_files.items('functions'):
  try:
    gp_eval.gp_function_declare(preconfigvar[0] + "=" + preconfigvar[1], functions)
  except KeyboardInterrupt: raise
  except:
    gp_error("Error importing function %s from configuration file:"%(preconfigvar[0]))
    gp_error("Error:" , sys.exc_info()[1], "(" , sys.exc_info()[0] , ")")
except KeyboardInterrupt: raise
except:
 pass # Ignore if no functions section 


# NOW IMPORT VARIABLES FROM CONFIGURATION FILE

try:
 for preconfigvar in config_files.items('variables'):
  try:
    variables[preconfigvar[0]] = gp_eval.gp_eval(preconfigvar[1], variables, functions)
  except KeyboardInterrupt: raise
  except:
    gp_warning("Warning: Expression '%s' for variable %s in configuration file could not be evaluated."%(preconfigvar[0],preconfigvar[1]))
except KeyboardInterrupt: raise
except:
 pass # Ignore if no variables section 

# NOW IMPORT COLOURS FROM CONFIGURATION FILE

colours_in  = config_lookup_str('colours','PALETTE','')
if (colours_in != ""):
 colours_in  = colours_in.split(',')
 colours_new = []
 for colour in colours_in:
  if (colour.strip().capitalize() in colours): colours_new.append(colour.strip().capitalize())
  else                                       : gp_error("Unrecognised colour '%s' in configuration file palette; skipping."%colour.strip())
 if (len(colours_new) == 0):
  gp_error("No colours found in configuration file palette; reverting to default palette.")
 else:
  colour_list_default = colours_new

colour_list = colour_list_default

# NOW IMPORT LATEX PREAMBLE FROM CONFIGURATION FILE

default_latex_preamble = config_lookup_str('latex','PREAMBLE','')
latex_preamble = default_latex_preamble

# Now that we have default settings, make copy them into initial settings

settings = settings_default.copy()
settings['GRIDAXISX'] = settings_default['GRIDAXISX'][:]
settings['GRIDAXISY'] = settings_default['GRIDAXISY'][:]

# By default, have one of each kind of axis... x1, y1 and z1
axes = {'x':{1:default_axis.copy()},
        'y':{1:default_axis.copy()},
        'z':{1:default_axis.copy()} }

#
# NOW IMPORT TERMINAL OPTIONS FROM CONFIGURATION FILE
#

terminal_colours = {"Normal": "\x1b[0m",
                    "Red":    "\x1b[01;31m",
                    "Green":  "\x1b[01;32m",
                    "Brown":  "\x1b[01;33m",
                    "Blue":   "\x1b[01;34m",
                    "Magenta":"\x1b[01;35m",
                    "Cyan":   "\x1b[01;36m",
                    "White":  "\x1b[01;37m"
                    }

display_splash = (config_lookup_opt('terminal','SPLASH','ON' ,onoff) == "ON") # Do we display welcome message?
coloursetting  = (config_lookup_opt('terminal','COLOUR','OFF',onoff) == "ON") # Do we use colour highlighting
if coloursetting: gp_error_setcolour()
else            : gp_error_setnocolour()
gp_error_setrepcol(config_lookup_opt2('terminal','COLOUR_REP','Green',terminal_colours))
gp_error_setwrncol(config_lookup_opt2('terminal','COLOUR_WRN','Brown',terminal_colours))
gp_error_seterrcol(config_lookup_opt2('terminal','COLOUR_ERR','Red'  ,terminal_colours))

# STORAGE OF DIRECTORY PATHS

# User's cwd, which we store here before setting cwd to a temporary folder for the duration of our activities
cwd = ""

# Make a directory into which we put temporary files
tempdirnumber = 1
file_paths=['foo']
while (len(file_paths) != 0): # Take care not to overright a pre-existing file in /tmp
 tempdirnumber = tempdirnumber + 1
 tempdir = "/tmp/gp+_" + str(os.getpid()) + "_" + str(tempdirnumber)
 file_paths=glob.glob(tempdir)
os.makedirs(tempdir,mode=0700)
if ((not os.path.isdir(tempdir)) or (not (os.stat(tempdir)[stat.ST_UID] == os.getuid()))):
 gp_error("Fatal Error: Security error whilst trying to create temporary directory")
 sys.exit(0)

# List of commands executed in this session, to be saved via save command
cmd_history = []
