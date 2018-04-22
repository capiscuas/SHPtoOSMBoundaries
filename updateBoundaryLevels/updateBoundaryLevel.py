# -*- coding: utf-8 -*-
# Use python2, since osm2python is not ported to python3

from osm2python.tree import load, dump
from collections import defaultdict

origin_osm_filename = 'boundaries.osm'
destiny_osm_filename = 'boundaries_updated.osm'

# loading the .osm file
osmtree = load(open(origin_osm_filename))

ways_min_admin_levels = defaultdict(int)
for i, r in osmtree.relations.items():
    if 'admin_level' in r.tags:
        admin_level = int(r.tags['admin_level'])
    else:
        print(r, 'has no admin_level')

    for way in r.members:
        if ways_min_admin_levels[way.ref] == 0 or ways_min_admin_levels[way.ref] > admin_level:
            ways_min_admin_levels[way.ref] = admin_level
            print(way.ref, admin_level)

for i, w in osmtree.ways.items():

    w.tags['admin_level'] = str(ways_min_admin_levels[i])
    print(i, w.tags)

# Saving to .osm
dump(open(destiny_osm_filename, 'w'), osmtree)
