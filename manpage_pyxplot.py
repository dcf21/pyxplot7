# MANPAGE_PYXPLOT.PY
#
# The code in this file is part of PyXPlot
# <http://www.pyxplot.org.uk>
#
# Copyright (C) 2006-7 Dominic Ford <coders@pyxplot.org.uk>
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

# Generate manpage for PyXPlot

import sys

docpath     = sys.argv[1]
author      = open("AUTHORS","r").read()
description = ""

f = open("README","r")
state = 0
for line in f.readlines():
 if   (line[0:2] == "1."): state = 1
 elif (line[0:2] == "2."): state = 2
 elif (state == 1)       : description += line

sys.stdout.write("""
.\" pyxplot.man
.\" Dominic Ford
.\" 21/02/2007

.\" Man page for pyxplot

.TH PYXPLOT 1
.SH NAME
pyxplot \- a commandline plotting package, with interface similar to that of
gnuplot, which produces publication-quality output.
.SH SYNOPSIS
.B pyxplot
[file ...]
.SH DESCRIPTION
%s
Full documentation can be found in:
%s
.SH COMMAND LINE OPTIONS
  -h, --help:       Display this help.
  -v, --version:    Display version number.
  -q, --quiet:      Turn off initial welcome message.
  -V, --verbose:    Turn on initial welcome message.
  -c, --colour:     Use coloured highlighting of output.
  -m, --monochrome: Turn off coloured highlighting.
.SH AUTHOR
%s.
.SH CREDITS
Thanks to Joerg Lehmann and Andre Wobst for writing the PyX graphics library
for python, upon which this software is heavily built, and also to Ross Church
for his many useful comments and suggestions during its development.
.SH "SEE ALSO"
.BR pyxplot_watch (1), gnuplot (1)
"""%(description,docpath,author))
