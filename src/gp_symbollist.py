# GP_SYMBOLLIST.PY
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

# A list of the symbol types used by the 'points' plot style

import dcfpyx
from dcfpyx import attr, path

# The following is a modified version of symbol definitions from the file:
# pyx/graph/style.py

# Upper Limit Symbol Definition

def _upperlimit_symbol(c, x_pt, y_pt, size_pt, attrs):
    c.draw(path.path(path.moveto_pt(x_pt-0.5*size_pt, y_pt             ),
                     path.lineto_pt(x_pt+0.5*size_pt, y_pt             )), attrs)
    c.draw(path.path(path.moveto_pt(x_pt            , y_pt             ),
                     path.lineto_pt(x_pt            , y_pt-2.0*size_pt )), attrs+[dcfpyx.deco.earrow(size=size_pt*dcfpyx.unit.v_pt)])

upperlimit = attr.changelist([_upperlimit_symbol])

# Lower Limit Symbol Definition

def _lowerlimit_symbol(c, x_pt, y_pt, size_pt, attrs):
    c.draw(path.path(path.moveto_pt(x_pt-0.5*size_pt, y_pt             ),
                     path.lineto_pt(x_pt+0.5*size_pt, y_pt             )), attrs)
    c.draw(path.path(path.moveto_pt(x_pt            , y_pt             ),
                     path.lineto_pt(x_pt            , y_pt+2.0*size_pt )), attrs+[dcfpyx.deco.earrow(size=size_pt*dcfpyx.unit.v_pt)])

lowerlimit = attr.changelist([_lowerlimit_symbol])

# List of symbol types, corresponding to point types 1,2,3,etc.

symbol_list = [[[dcfpyx.graph.style.symbol.cross   ,False]],
               [[dcfpyx.graph.style.symbol.plus    ,False]],
               [[dcfpyx.graph.style.symbol.cross   ,False] , [dcfpyx.graph.style.symbol.plus    ,False]],
               [[dcfpyx.graph.style.symbol.square  ,False]],
               [[dcfpyx.graph.style.symbol.triangle,False]],
               [[dcfpyx.graph.style.symbol.circle  ,False]],
               [[dcfpyx.graph.style.symbol.diamond ,False]],
               [[dcfpyx.graph.style.symbol.square  ,True ]],
               [[dcfpyx.graph.style.symbol.triangle,True ]],
               [[dcfpyx.graph.style.symbol.circle  ,True ]],
               [[dcfpyx.graph.style.symbol.diamond ,True ]],
               [[upperlimit                     ,False]],
               [[lowerlimit                     ,False]]
               ]

