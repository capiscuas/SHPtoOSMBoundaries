#!/usr/bin/python
"""
A sample script that exports OSM XML document to a simple json structure.

Usage:
$ python osm_json.py my_file.osm[.bz2] > output.json

{
	name: 'node',
	attrs: {
		id: 321,
		version: 2,
		...
	},
	children: [
		{
			name: 'tag',
			attrs: {
				k: 'highway',
				v: 'crossing'
			}
		}
	],
	...
}
"""

import json
import sys
import bz2

from __init__ import load_osm


def parse_json(infile, outfile):
	def callback(elt, parent):
		if elt['name'] in ('node', 'way', 'relation'):
			if not elt['children']:
				del elt['children']
			json.dump(elt, outfile, indent=4)
		else:
			del elt['children']
			parent['children'].append(elt)

	load_osm(infile, load_callback=callback)


if __name__ == '__main__':
	infilename = sys.argv[1]

	open_func = bz2.BZ2File if infilename.endswith('.bz2') else open
	with open_func(infilename, 'r') as infile:
		parse_json(infile, sys.stdout)
