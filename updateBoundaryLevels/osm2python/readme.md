osm2python : A  Simple Python OSM XML Converter
===========

Usage is extremely simple:

    >>> from osm2python import load_osm, dump_osm
    >>> load_osm(open('my_file.osm'))
    [<a list of all the XML elements as dictionaries (see help(load_osm) for more info)>]

Dump it back:

    >>> dump_osm(open('another_file.osm', 'w'), new_doc_dictionary)

If you want to save the elements into a custom storage, define a callback:

    >>> def cb(current, parent):
            print current

    >>> load_osm(open('my_file.osm'), cb)
    (will just print all the dictionaries)

You can also create an arbitrary filter for the elements:

    >>> flt = lambda elt: (elt['name'] == 'node' and
           (54 < int(elt['attrs']['lat']) < 56) and
           (82 < int(elt['attrs']['lon']) < 84))

    >>> load_osm(open('my_file.osm'), element_filter=flt)
    <list of dictionaries>

Tests with bzipped files show that the scripts run twice as faster in [PyPy][1] 1.8 than in cPython 2.7.2, but since this script keeps all the data in memory, the memory usage with PyPy becomes impractically big on real OSM files. So, to run with PyPy, make sure your callback does not store references to the new elements, so that they could be garbage-collected. To run such a test, do

    $ python __init__.py sample/chistooz.osm.bz2 x
    $ path/to/pypy __init__.py sample/chistooz.osm.bz2 x

(the second argument 'x' triggers profiling)

**tree.py** can import from OSM XML in Python objects representing the document and linking correctly one another.

**osm_json.py** dumps these dictionaries in json format.

Note: This project is not a PyPI package yet.

   [1]: http://pypy.org/
