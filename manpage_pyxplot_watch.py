# MANPAGE_PYXPLOT_WATCH.PY
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

# Generate manpage for PyXPlot watcher

import sys

docpath     = sys.argv[1]
author      = open("AUTHORS","r").read()
description = ""

sys.stdout.write(r"""
.\" pyxplot_watch.man
.\" Dominic Ford
.\" 17/11/2009

.\" Man page for pyxplot_watch

.TH PYXPLOT_WATCH 1
.SH NAME
pyxplot_watch \- a tool which monitors a collection of PyXPlot command scripts
and executes them whenever they are modified.
.SH SYNOPSIS
.B pyxplot_watch
[file ...]
.SH DESCRIPTION
pyxplot_watch is a part of the PyXPlot plotting package; it is a simple tool
for watching PyXPlot command script files, and executing them whenever they are
modified. It is should be followed on the commandline by a list of command
scripts which are to be watched.  Full documentation can be found in:
%s
.SH COMMAND LINE OPTIONS
  \-v, \-\-verbose: Verbose mode; output full activity log to terminal
  \-q, \-\-quiet  : Quiet mode; only output PyXPlot error messages to terminal
  \-h, \-\-help   : Display this help
  \-V, \-\-version: Display version number
.SH AUTHOR
%s.
.SH CREDITS
Thanks to Joerg Lehmann, Andre Wobst and Michael Schindler for writing the PyX
graphics library for python, upon which this software is heavily built.  Thanks
must also go to all of the users who have got in touch with us by email since
PyXPlot was first released on the web. Your feedback and suggestions have been
gratefully received.
.SH "SEE ALSO"
.BR pyxplot (1), gnuplot (1)
"""%(docpath,author))
