import xml.etree.cElementTree as ET
#import xml.dom.minidom as minidom

from shapely.geometry import LineString,MultiLineString
import json


#Set MAINTENANCE True if you want a tofix_splittedways.osm file be generated with the cleaned splitted ways geojson
#This is useful for example if you want to join TOO SMALL segments using JOSM
#Make sure to save it as .geojson format and with the filename indicaded as SPLITTED_WAYS_GEOJSON and rerun this script setting MAINTENANCE = False
MAINTENANCE = False
ALL_LEVELS_GEOJSON = 'fiji_level8.geojson'
#Now the SPLITTED_WAYS_GEOJSON file we create it from the ALL_LEVELS_GEOJSON files one by using QGIS and converting polygons to lines
#and breaking the lines using the .break function of the GRASS plugin
SPLITTED_WAYS_GEOJSON = 'fiji_splitted.geojson'

OTHER_LEVELS = [{"level":"6", "uniquetag": "PID" ,"nametag":"PROVINCE"}]
DEEPER_LEVEL = {"level":"8", "uniquetag": "TID" ,"nametag":"TIKINA"}



#DON'T MODIFY THE CODE FROM DOWN HERE UNLESS YOU KNOW PYTHON OR LIKE TO HACK AROUND.
all_levels_num = [DEEPER_LEVEL["level"]]
upper_rel = {}
relations = {}
boundarynames = {}

for l in OTHER_LEVELS:
    n = l["level"]
    upper_rel[n] = dict()
    all_levels_num.append(n)
    
for n in all_levels_num:
    relations[n] = dict()
    boundarynames[n] = dict()

unique_nodes = {}
node_counter = -1
def getUniqueNodeId(point):
    global node_counter
    global unique_nodes
    lonlat = str(point[0]) + "," + str(point[1])
    if  not unique_nodes.has_key(lonlat):
        node_counter -= 1
        unique_nodes[lonlat] = node_counter
        return node_counter
    else: return unique_nodes[lonlat]



def reduceFloat(geom):
    new_geom = []
    for p in geom:
        #print p
        p = [float("{0:.5f}".format(p[0])), float("{0:.5f}".format(p[1]))]
        new_geom.append(p)
    return new_geom



#Loading the Geojson with the boundaries
def fillingLevelWays(data,uniquetag):
    boundaries = {}
    for feature in data['features']:
        if not feature['properties']: continue
        uniqueidentif = feature['properties'][uniquetag]
        boundaries[uniqueidentif] = {'properties': feature['properties']}
        poligon = feature['geometry']['coordinates']
        lines = []
        for i in poligon:
            for geom in i:
                lines.append(LineString(reduceFloat(geom)))
        boundaries[uniqueidentif]["geometry"] = MultiLineString(lines)
    return boundaries




def addEdgePoint(edgepoints_ocurrences,point_id):
    if edgepoints_ocurrences.has_key(point_id):
        edgepoints_ocurrences[point_id] += 1
    else: edgepoints_ocurrences[point_id] = 1
    
    
def recalculateEdges(tempways):
    edgepoints_ocurrences = {}
    for way in tempways:
        addEdgePoint(edgepoints_ocurrences, getUniqueNodeId(way.coords[0]))
        addEdgePoint(edgepoints_ocurrences, getUniqueNodeId(way.coords[-1]))
    return edgepoints_ocurrences



#f = open("tofix.geojson", 'w')
##fc = geojson.FeatureCollection(features)
#f.write(json.dumps(mapping(multiline)) )
#f.close()        

def save(uniqueways_ref,unique_nodes,allrelations,output_filename):
    osm_header = "<?xml version='1.0' encoding='UTF-8'?>\n<osm version='0.6' upload='true' generator='JOSM'>\n</osm>"
    r = ET.fromstring(osm_header)

    #Creating the ways part in the .osm
    #print uniqueways_ref
    print "Saving Ways"
    for way_ref,line in uniqueways_ref.items():
        #way_ref = feature['properties']["way_ref"]
        xml_way = ET.Element('way',{'id':'-'+str(way_ref), 'visible':'true'})
        #points =  feature["geometry"]["coordinates"]
        for p in line.coords:
            node_id = getUniqueNodeId(p)
            xml_way.append(ET.Element('nd',{'ref':str(node_id)}))
        r.append(xml_way)
    
    print "Saving Nodes"
    for lonlat , n_id in unique_nodes.items():
        lon = lonlat.split(",")[0]
        lat = lonlat.split(",")[1]
        xml_node = ET.Element('node',{'id':str(n_id), 'visible':'true','lat':str(lat) ,'lon':str(lon)})
        xml_node
        r.append(xml_node)
    
#Printing the XML for debug purpose with pretty format
#xmlstr = minidom.parseString(ET.tostring(r)).toprettyxml(indent="   ")
#with open(output_filename, "w") as f:
   #f.write(xmlstr)
    
    print "Saving Relations"
    counter = 1000000
    for level, all_relations_level in allrelations.items():
        print("Export relations level",level)
        print(len(all_relations_level))
        
        for code, rel in all_relations_level.items():
                ways = rel["ways"]
                #print len(ways)
                #print code
                xml = ET.Element('relation',{'id':'-'+str(counter), 'visible':'true'})
                #In case the name is all capital letters, here you can convert it
                name = rel["boundaryname"].title()
                identif = rel["identif"]
                xml.append(ET.Element('tag',{'k':'boundary','v':'administrative'}))
                xml.append(ET.Element('tag',{'k':'admin_level','v':level}))
                xml.append(ET.Element('tag',{'k':'type','v':'boundary'}))
                xml.append(ET.Element('tag',{'k':'sourceTool','v':'SHPtoOSMBoundaries v0.2'}))
                #xml.append(ET.Element('tag',{'k':'natural','v':'water'}))
                xml.append(ET.Element('tag',{'k':'ID','v':str(identif)}))
                xml.append(ET.Element('tag',{'k':'name','v':name}))
                
                for way_ref in ways:
                    #way_ref = indexes[1:indexes.find(',')] +  indexes[indexes.find(',')+2:] #we remove the , comma
                    xml.append(ET.Element('member',{'type':'way','role':'outer','ref':'-'+str(way_ref)}))
                r.append(xml)
                counter += 1

    print "Saving to",output_filename
    file_out = open(output_filename, "w")
    file_out.write(ET.tostring(r, encoding='utf-8')) 
    file_out.close()
 
def addWayToRelation(level,identif,boundaryname,way_ref):
    if relations[level].has_key(identif):
                relations[level][identif]["ways"].append(way_ref)
    else: 
                relations[level][identif] = {"boundaryname":boundaryname, "identif":identif, "ways":[way_ref]}


#We loop each of the unique splitted ways trough the boundaries for all the levels
def detect_relations(way,way_ref,level,level_ways):
    total_founds = 0

    for code,way_with_tags in level_ways.items():
        #boundaryname = way_with_tags["properties"][DEEPER_LEVEL["nametag"]]
        #print boundaryname
        if way.within(way_with_tags["geometry"]):
            #print "Found within"
            
            deeperlevel_uniquetag = DEEPER_LEVEL["uniquetag"]
            deeperlevel_nametag =  DEEPER_LEVEL["nametag"]
            deeper_level_num = DEEPER_LEVEL["level"]
            #print deeper_level_num,deeperlevel_nametag,deeperlevel_uniquetag
            boundaryname = way_with_tags["properties"][deeperlevel_nametag]
            identif =  way_with_tags["properties"][deeperlevel_uniquetag]
            addWayToRelation(str(deeper_level_num),identif,boundaryname,way_ref)
            
            for eachlevel in OTHER_LEVELS:
                
                eachlevel_uniquetag = eachlevel["uniquetag"]
                eachlevel_nametag =  eachlevel["nametag"]
                eachlevel_num = eachlevel["level"]
                boundary_id = way_with_tags["properties"][eachlevel_uniquetag]
                boundarynames[eachlevel_num][boundary_id] = way_with_tags["properties"][eachlevel_nametag]
                #In the next FOR loop, we will see if this way is a border between two upper level if the tags differ
                if upper_rel[eachlevel_num].has_key(way_ref):
                    upper_rel[eachlevel_num][way_ref].append(boundary_id)
                else:
                    upper_rel[eachlevel_num][way_ref] = [boundary_id]
            
            total_founds += 1
            if total_founds == 2:
                break
    
    


####EXPORTING TO THE XML######


#print 'Erase all nodes from the XML tree'
##for i in r.findall("node"):
    ##r.remove(i)

##print 'Erase all the ways from the XML Tree'
##for way in r.findall("way"):
    ##r.remove(way)

def main():

    #We use the splitted geojson with all the 
    with open(SPLITTED_WAYS_GEOJSON) as f:
        data = json.load(f)


    print("Initial lines (), Total:",len(data['features']))

    count = 0
    way_ref = 0
    uniqueways = []
    

    for feature in data['features']:
        geom = feature['geometry']['coordinates']
        if geom:
            uniqueways.append(LineString(reduceFloat(geom)))
            

    #print("After removing overlapping lines, Total:",len(uniqueways))

    edgepoints_ocurrences = recalculateEdges(uniqueways)
    print("Total way edges",len(edgepoints_ocurrences))
    vertices = []
    for point_id,ocurrence in edgepoints_ocurrences.items():
        #if ocurrence > 2:
            vertices.append(point_id)
        #if ocurrence < 2:

    print("Total vertices",len(vertices))
    #print vertices

    post_uniqueways = []
    for way in uniqueways:
        #print len(way.coords)
        splitted = False
        for n,coord in enumerate(way.coords):
                if n != 0 and n != len(way.coords)-1:
                    #print "searching"
                    if getUniqueNodeId(coord) in vertices:
                        print "Found vertice in middle of way, search in JOSM as ",coord[1]," ",coord[0]
                        #print n
                        #print way.coords[:n+1]
                        way1 = LineString(way.coords[:n+1])
                        #print way.coords[n:]
                        way2 = LineString(way.coords[n:])
                        post_uniqueways.append(way1)
                        post_uniqueways.append(way2)
                        splitted = True
                        break
        if not splitted:
                post_uniqueways.append(way)

    uniqueways = post_uniqueways
    print("After splitting those ways, Total:",len(uniqueways))

    post_uniqueways = []
    for way in uniqueways:
        repeated = False
        if count % 100 == 0:
            print(count)
        count += 1
        
        for line in post_uniqueways:
            if way.within(line):
                repeated = True
                break
        if not repeated:
            post_uniqueways.append(way)

    uniqueways = post_uniqueways
    print("After removing overlapping lines, Total:",len(uniqueways))


    #Joining the little segments within vertices

    print "Recalculating Edge Points"
    edgepoints_ocurrences = recalculateEdges(uniqueways)
    print("Total way edges",len(edgepoints_ocurrences))
    
    
    if MAINTENANCE:
        uniqueways_ref = {}
        way_ref = 1
        for way in uniqueways:
            way_ref += 1
            uniqueways_ref[way_ref] = way
            if way_ref % 100 == 0:
                print(way_ref)
            
        save(uniqueways_ref,unique_nodes,{},"tofix_splittedways.osm")
        print "A maintenance 'tofix_splittedways.osm' file was generated in case further cleaning needs to be done with JOSM."
        print "Once finished, replace it as '",SPLITTED_WAYS_GEOJSON,"', set the MAINTENANCE setting to False and rerun this script."
        exit()
#####END OF CLEANING THE SPLITTED WAYS FILE
   
    print ("Loading ALL Levels file")
    with open(ALL_LEVELS_GEOJSON) as f:
        data = json.load(f)
        
    deeperlevel_uniquetag =  DEEPER_LEVEL["uniquetag"]
    all_levels_ways = fillingLevelWays(data,deeperlevel_uniquetag)
    print(len(all_levels_ways),"polygons found.")

    way_ref = 1          
    uniqueways_ref = {}
    deeper_level_num = str(DEEPER_LEVEL["level"])
    for way in uniqueways:
        way_ref += 1
        uniqueways_ref[way_ref] = way
        detect_relations(way,way_ref,deeper_level_num,all_levels_ways)
        if way_ref % 100 == 0:
            print(way_ref)
            
    #If the way has the same upper boundaries in each side, we ignore it(NOT A BOUNDARY BORDER),
    #otherwise, it is a border between boundary relation and we add it.
    for level,way_refs in upper_rel.items():
        for way_ref,uniqueidentifiers in way_refs.items():
            if len(uniqueidentifiers) > 1:
                if uniqueidentifiers[0] != uniqueidentifiers[1]:
                    identif = uniqueidentifiers[0]
                    boundaryname = boundarynames[level][identif]
                    addWayToRelation(level,identif,boundaryname,way_ref)
                    
                    identif = uniqueidentifiers[1]
                    boundaryname = boundarynames[level][identif]
                    addWayToRelation(level,identif,boundaryname,way_ref)
            else:
                identif = uniqueidentifiers[0]
                boundaryname = boundarynames[level][identif]
                addWayToRelation(level,identif,boundaryname,way_ref)   
    
    #for level, all_relations_level in relations.items():
        #print level
        #print len(all_relations_level)
        
    save(uniqueways_ref,unique_nodes,relations,"final.osm")


if __name__ == "__main__":
    main()
