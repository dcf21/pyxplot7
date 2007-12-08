# MAKEFILE
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

# Makefile for PyXPlot documentation directory

PYXPLOT = `which pyxplot`
EXAMPLEDIR = examples
EPSDIR = $(EXAMPLEDIR)/eps
EPSFILES = $(EPSDIR)/ex_cover.eps $(EPSDIR)/ex_axislab.eps $(EPSDIR)/ex_multiaxes.eps $(EPSDIR)/ex_axistics.eps $(EPSDIR)/ex_legends.eps $(EPSDIR)/ex_seminar.eps $(EPSDIR)/ex_barchart1.eps $(EPSDIR)/ex_barchart2.eps $(EPSDIR)/ex_funcsplice1.eps $(EPSDIR)/ex_funcsplice2.eps

all: $(EPSFILES) pyxplot.pdf

clean:
	rm -Rf $(EPSDIR)
	rm -f pyxplot.pdf pyxplot.ps pyxplot.dvi *.aux *.idx *.ilg *.ind *.log *.toc
	rm -Rf html

$(EPSDIR)/%.eps: $(EXAMPLEDIR)/%.ppl
	echo "Producing example plot $*..."
	mkdir -p $(EPSDIR)
	$(PYXPLOT) $< > /dev/null

%.pdf: %.ps
	echo "Making pdf documentation..."
	ps2pdf $< $@ > /dev/null 2> /dev/null

%.ps: %.dvi
	echo "Making postscript documentation..."
	dvips -Pcmz -Pamz $< -o $@ > /dev/null 2> /dev/null

%.dvi: %.tex
	echo "Compiling documentation..."
	latex $< > /dev/null 2> /dev/null
	latex $< > /dev/null 2> /dev/null
	latex $< > /dev/null 2> /dev/null
	makeindex pyxplot.idx > /dev/null 2> /dev/null
	latex $< > /dev/null 2> /dev/null
