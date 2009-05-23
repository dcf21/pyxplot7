# GP_TEXT.PY
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

# Contains text messages which pyxplot displays

import os
import re

import gp_version # Version and date strings written by installer

VERSION = gp_version.VERSION
DATE    = gp_version.DATE

version = r"""PyXPlot """+VERSION

help = version + "\n" + re.sub(".","-",version) + r"""

Usage: pyxplot <options> <filelist>
  -h, --help:       Display this help.
  -v, --version:    Display version number.
  -q, --quiet:      Turn off initial welcome message.
  -V, --verbose:    Turn on initial welcome message.
  -c, --colour:     Use coloured highlighting of output.
  -m, --monochrome: Turn off coloured highlighting.

A brief introduction to PyXPlot can be obtained by typing 'man pyxplot'; the
full Users' Guide can be found in the file:
"""+os.path.join(gp_version.DOCDIR,"pyxplot.pdf")+r"""

For the latest information on PyXPlot development, see the project website:
<http://www.pyxplot.org.uk>"""

init = r"""
 ____       __  ______  _       _      PYXPLOT
|  _ \ _   _\ \/ /  _ \| | ___ | |_    Version """+VERSION+r"""
| |_) | | | |\  /| |_) | |/ _ \| __|   """+DATE+r"""
|  __/| |_| |/  \|  __/| | (_) | |_
|_|    \__, /_/\_\_|   |_|\___/ \__|   Copyright (C) 2006-9 Dominic Ford
       |___/                                         2008-9 Ross Church

With thanks to Joerg Lehmann, Andre Wobst and Michael Schindler for writing
PyX.

Send comments, bug reports, feature requests and coffee supplies to:
<coders@pyxplot.org.uk>
"""

invalid = r"""
 %s
/|\
 |
Error: Unrecognised command.
"""

valid_set_options = r"""
'arrow', 'autoscale', 'axescolour', 'axis', 'backup', 'bar', 'boxfrom',
'boxwidth', 'data style', 'display', 'dpi', 'fontsize', 'function style',
'grid', 'gridmajcolour', 'gridmincolour', 'key', 'keycolumns', 'label',
'linestyle', 'linewidth', 'logscale', 'multiplot', 'noarrow', 'noaxis',
'nobackup', 'nodisplay', 'nogrid', 'nokey', 'nolabel', 'nolinestyle',
'nologscale', 'nomultiplot', 'no<m>[xyz]<n>tics', 'notitle', 'origin',
'output', 'palette', 'papersize', 'pointlinewidth', 'pointsize', 'preamble',
'samples', 'size', 'size noratio', 'size ratio', 'size square', 'terminal',
'textcolour', 'texthalign', 'textvalign', 'title', 'width', '[xyz]<n>label',
'[xyz]<n>range', '[xyz]<n>ticdir', '<m>[xyz]<n>tics'
"""

valid_show_options = r"""
'autoscale', 'axescolour', 'backup', 'bar', 'boxfrom', 'boxwidth', 'colour,
'data style', 'display', 'dpi', 'fontsize', 'function style', 'grid',
'gridmajcolour', 'gridmincolour', 'key', 'keycolumns', 'label', 'linestyle',
'linewidth', 'logscale', 'multiplot', 'origin', 'output', 'palette',
'papersize', 'pointlinewidth', 'pointsize', 'preamble', 'samples', 'size',
'terminal', 'textcolour', 'texthalign', 'textvalign', 'title', 'width',
'[xyz]<n>label', '[xyz]<n>range', '[xyz]<n>ticdir', '[xyz]<n>tics'
"""

set_noword = r"""
Set options which PyXPlot recognises are: [] = choose one, <> = optional
"""+valid_set_options+"""
Set options from gnuplot which PyXPlot DOES NOT recognise:

'angles', 'border', 'clabel', 'clip', 'cntrparam', 'colorbox', 'contour',
'decimalsign', 'dgrid3d', 'dummy', 'encoding', 'format', 'hidden3d',
'historysize', 'isosamples', 'locale', '[blrt]margin', 'mapping', 'mouse',
'offsets', 'parametric', 'pm3d', 'polar', 'print', '[rtuv]range', 'style',
'surface', 'ticscale', 'ticslevel', 'timestamp', 'timefmt', 'view',
'[xyz]{2}data', '{[xyz]{2}}zeroaxis', 'zero'
"""

unset_noword = r"""
Unset options which PyXPlot recognises are: [] = choose one, <> = optional

'arrow', 'autoscale', 'axescolour', 'axis', 'backup', 'bar', 'boxfrom',
'boxwidth', 'display', 'dpi', 'fontsize', 'grid', 'gridmajcolour',
'gridmincolour', 'key', 'keycolumns', 'label', 'linestyle', 'linewidth',
'logscale', 'multiplot', 'noarrow', 'noaxis', 'nobackup', 'nodisplay',
'nogrid', 'nokey', 'nolabel', 'nolinestyle', 'nolinewidth', 'nologscale',
'nomultiplot', 'no<m>[xyz]<n>tics', 'origin', 'output', 'palette', 'papersize',
'pointlinewidth', 'pointsize', 'preamble', 'samples', 'size', 'terminal',
'textcolour', 'texthalign', 'textvalign', 'title', 'width', '[xyz]<n>label',
'[xyz]<n>range', '[xyz]<n>ticdir', '<m>[xyz]<n>tics'
"""

set = r"""
Error: Invalid set option '%s'.

"""+set_noword

unset = r"""
Error: Invalid unset option '%s'.

"""+unset_noword

show = r"""
Valid 'show' options are:

'all', 'arrows', 'axes', 'settings', 'labels', 'linestyles', 'variables',
'functions'

or any of the following set options:
"""+valid_show_options
