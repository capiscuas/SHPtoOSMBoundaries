"""
A sample module that generates a class-based elements tree from OSM XML and converts it back to XML.

Import load() and dump() to import or export the classes structure.

This example imports OSM document, re-exports it to XML and prints the contents to the system shell:

>>> from tree import load, dump
>>> dump(sys.stdout, load(sys.stdin))

Call this script from the shell, for testing or benchmarking purposes:

$ python tree.py my_document.osm[.bz2] > test.osm

or

$ python tree.py one.osm.bz2 | bzip2 -z > two.osm.bz2
"""

import bz2
from itertools import chain
import sys

from __init__ import load_osm, dump_osm


class GeneralMixin(object):
	"""
	An auxilliary class. Contains the most common methods for all the OSM elements.
	"""
	def __init__(self, doc, data):
		self.doc = doc
		self.attrs = data['attrs']
		self.tags = {item['attrs']['k']: item['attrs']['v'] for item in self.filter_children(data, 'tag')}

	@staticmethod
	def filter_children(element, tag_name):
		"""
		Extracts from `element` the child elements named `tag_name`, e.g.: self.filter_children(data, 'tag')
		"""
		return (i for i in element['children'] if i['name'] == tag_name)

	@property
	def tags_dict(self):
		"""
		Converts tags dictionary into dictionaries that represent XML elements.
		"""
		return ({'name': 'tag', 'attrs': {'k': k, 'v': v}} for k, v in self.tags.items())

	@property
	def attrs_dict(self):
		"""
		Some classes have same data dict structure (may or may not contain children), but may have different attributes.

		Node and Member redefine this property.
		"""
		return self.attrs

	@property
	def as_dict(self):
		"""
		Dumps the whole element into the common dictionary structure (defined in __init__.py).
		"""
		return {'name': self.name, 'attrs': self.attrs_dict, 'children': self.tags_dict}

	@staticmethod
	def ref(element):
		"""
		Takes the ref attribute from `element` and converts it to integer.
		"""
		return int(element['attrs']['ref'])


class ElementMixin(GeneralMixin):
	"""
	Element mixin introduces ids: ids are popped from attributes when initialized and added when dumped to a dict. Also ids are used for string representation.
	"""
	def __init__(self, doc, data):
		super(ElementMixin, self).__init__(doc, data)
		self.id = int(self.attrs.pop('id'))

	def __repr__(self):
		return '%s %s' % (self.__class__.__name__, self.id)

	@property
	def attrs_dict(self):
		d = super(ElementMixin, self).attrs_dict
		d['id'] = self.id
		return d


class Node(ElementMixin):
	"""
	OSM Node class
	"""
	name = 'node'

	def __init__(self, doc, data):
		super(Node, self).__init__(doc, data)
		self.lat, self.lon = map(float, map(data['attrs'].pop, ('lat', 'lon')))  # 1337 :D

	@property
	def attrs_dict(self):
		d = super(Node, self).attrs_dict
		d.update({'lon': self.lon, 'lat': self.lat})
		return d


class Way(ElementMixin):
	"""
	OSM Way class
	"""
	name = 'way'

	def __init__(self, doc, data):
		super(Way, self).__init__(doc, data)
		self.nodes = [self.doc.nodes[self.ref(nd)] for nd in self.filter_children(data, 'nd')]

	@property
	def as_dict(self):
		data = super(Way, self).as_dict
		data['children'] = chain(
			data['children'],
			({'name': 'nd', 'attrs': {'ref': node.id}} for node in self.nodes),
		)
		return data


class Member(GeneralMixin):
	"""
	OSM Relation membership class. Is standalone, since membership also has role to it, which belongs neither to the relation, nor to the member element.
	"""
	name = 'member'

	def __init__(self, relation, data):
		self.relation = relation
		self.attrs = data['attrs']
		self.role = self.attrs.pop('role')
		self.member_type = self.attrs.pop('type')
		self.ref = self.ref(data)

	@property
	def tags(self):
		# Relation member elements contain no tags.
		return {}

	@property
	def member(self):
		return self.relation.doc.dicts[self.member_type][self.ref]

	@member.setter
	def member(self, new_member):
		self.ref = new_member.id
		self.member_type = new_member.name

	def __repr__(self):
		return '%s %s in %s as %s' % (self.__class__.__name__, self.member, self.relation, self.role)

	@property
	def attrs_dict(self):
		return {'ref': self.ref, 'type': self.member_type, 'role': self.role}


class Relation(ElementMixin):
	"""
	OSM Relation class. Contains Member instances in self.members, which lead to the real relation members (nodes, ways or other relations).
	"""
	name = 'relation'

	def __init__(self, doc, data):
		super(Relation, self).__init__(doc, data)
		self.members = [Member(self, i) for i in self.filter_children(data, 'member')]

	@property
	def as_dict(self):
		data = super(Relation, self).as_dict
		data['children'] = chain(
			data['children'],
			(m.as_dict for m in self.members),
		)
		return data


class OsmDocument(object):
	"""
	A pure container. Packs nodes, ways and relations together.
	"""
	classes = {
		'node': Node,
		'way': Way,
		'relation': Relation,
	}

	def __init__(self):
		self.nodes = {}
		self.ways = {}
		self.relations = {}
		self.dicts = {
			'node': self.nodes,
			'way': self.ways,
			'relation': self.relations,
		}


def load(stream):
	"""
	Imports OSM XML document from `stream`, returns a named tuple with .nodes, .ways and .relations with the document elements.
	"""
	doc = OsmDocument()

	def load_callback(current, parent):
		"""
		Does nothing. Overriden for safety.
		"""
		name = current['name']
		if name in doc.classes:
			d = doc.dicts[name]
			element = doc.classes[name](doc, current)
			d[element.id] = element
		else:
			parent['children'].append(current)

	load_osm(stream, load_callback=load_callback)
	return doc


def dump(stream, doc):
	"""
	Exports the `doc` OsmDocument instance into OSM XML and dumps it into `stream`.
	"""
	items = (elt.as_dict for i, elt in chain(
		doc.nodes.items(),
		doc.ways.items(),
		doc.relations.items()
	))
	dump_osm(stream, items)


if __name__ == '__main__':
	infilename = sys.argv[1]
	open_func = bz2.BZ2File if infilename.endswith('.bz2') else open
	with open_func(infilename) as infile:
		if len(sys.argv) > 2:
			from cProfile import Profile
			p = Profile()
			stat = p.runctx('dump(tgt, load(src))', {'load': load, 'dump': dump, 'src': infile, 'tgt': sys.stdout}, {})
			stat.print_stats()

		else:
			dump(sys.stdout, load(infile))
