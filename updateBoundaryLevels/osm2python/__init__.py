#!/usr/bin/python
"""
Author: Dmitri Lebedev https://bitbucket.org/siberiano/osm2python/overview
Python OSM XML converter.

Usage is extremely simple:

>>> from osm2py import load_osm
>>> load_osm(open('my_file.osm'))
[<a list of all the XML elements as dictionaries (see help(load_osm) for more info)>]

If you want to save the elements into a custom storage, define a callback:

>>> def cb(current, parent):
        print current

>>> load_osm(open('my_file.osm'), cb)
(will just print all the dictionaries)

You can also create an arbitrary filter for the elements:
>>> flt = lambda elt: elt['name'] == 'node' and (54 < int(elt['attrs']['lat']) < 56) and (82 < int(elt['attrs']['lon']) < 84)
>>> load_osm(open('my_file.osm'), element_filter=flt)
<list of dictionaries>

osm_json.py dumps these dictionaries in json format.

tree.py can import from OSM XML in Python objects representing the document and linking correctly one another.
"""
import xml.parsers.expat
import xml.sax.saxutils

allowed = 'bounds bound tag node way nd member relation'.split()


def default_element_filter(element):
	"""
	Override this function to filter elements as you need. The overridden function will be called like this: element_filter(**{'name': ..., 'attrs': ...})
	"""
	return element['name'] in allowed


def load_osm(stream, load_callback=None, element_filter=None):
	"""
	Loads data from OSM file `stream` into wherever, filtering the XML elements with `element_filter` and calling `load_callback` with them. By default, the data is saved as a dictionaries hierarchy and returned.

	`element_filter` will receive a single parameter, a dictionary describing the element, and must return a boolean, whether to remember this element or not.
	{
		'name': 'way',
		'attrs': {'id': 1357, 'user': 'siberiano', ...},
		'tags': {'highway': 'primary', 'oneway': 'yes', 'lanes': '3'},
		'children': [ a list of similar dictionaries ]
	}

	If `element_filter` returns True, at the end of the element `load_callback` will be called, with the element (the same dictionary instance), plus the parent element dictionary. The parent will NOT contain the current element. Instead, it's `load_callback`'s duty to save it somewhere (in parent['children'] for instance).

	In the end, load_osm will return the `elements` list.
	"""

	# saving into closure
	load_osm.current = None
	load_osm.stack = []
	load_osm.elements = []

	if not load_callback:
		def load_callback(current, parent):
			parent['children'].append(current)

	element_filter = element_filter or default_element_filter

	def start_element(name, attrs):
		new_current = {'name': name, 'attrs': attrs, 'children': []}
		if element_filter(new_current) and load_osm.current:
			load_osm.stack.append(load_osm.current)
		load_osm.current = new_current

	def end_element(name):
		if load_osm.current and element_filter(load_osm.current):
			parent = load_osm.stack.pop() if load_osm.stack else load_osm.elements
			load_callback(load_osm.current, parent)
			load_osm.current = parent

	p = xml.parsers.expat.ParserCreate()
	p.StartElementHandler = start_element
	p.EndElementHandler = end_element
	p.ParseFile(stream)

	return load_osm.elements


def _dump_element(doc, elt, level=0):
	"""
	A recursive function that dumps an element into XML document tree.
	"""
	doc.characters('  ' * level)
	doc.startElement(elt['name'], attrs={k: unicode(v) for k, v in elt.get('attrs', {}).items()})

	if 'children' in elt:
		doc.characters('\n')
		for child in elt['children']:
			_dump_element(doc, child, level + 1)

	doc.characters('  ' * level)
	doc.endElement(elt['name'])
	doc.characters('\n')


def dump_osm(stream, elements, osm_attrs=None):
	"""
	Generates an OSM XML document from `elements` sequence.
	The `elements` sequence must return dictionaries like the following:
	{
		'name': element_name,
		'attrs': {'id': 573, 'user': 'siberiano', 'timestamp': '2012-03-21 17:55:24Z'},
		'tags': {'highway': 'primary', 'oneway': 'yes'},
		'children': <children sequence>,
	}

	'tags' and 'children' keys are optional. Hint: `children` sequence can be a recursive generator that extracts dictionaries from somewhere.
	"""
	if not hasattr(elements, '__iter__'):
		raise ValueError('Elements must be an iterable')

	osm_attrs = osm_attrs or {'version': '0.6'}

	doc = xml.sax.saxutils.XMLGenerator(stream, 'UTF-8')
	doc.startDocument()
	_dump_element(doc, {'name': 'osm', 'attrs': osm_attrs, 'children': elements})
	doc.endDocument()


if __name__ == '__main__':
	import bz2
	import sys
	infilename = sys.argv[1]
	open_func = bz2.BZ2File if infilename.endswith('.bz2') else open
	with open_func(infilename) as infile:
		if len(sys.argv) > 2:
			from cProfile import Profile
			p = Profile()
			stat = p.runctx('dump(tgt, load(src))', {'load': load_osm, 'dump': dump_osm, 'src': infile, 'tgt': sys.stdout}, {})
			stat.print_stats()

		else:
			dump_osm(sys.stdout, load_osm(infile))
