#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 08:07:59 2022

@author: joe
"""

#

#required dependencies

import laspy
import numpy as np
import pandas as pd
import json
from pyproj import Transformer
import math
from scipy.spatial import ConvexHull, convex_hull_plot_2d
import matplotlib.pyplot as plt
import matplotlib.path as mpltPath
import datetime
from multiprocessing import Pool

#

def processLas(lasFileName):
    '''
    
    Parameters
    ----------
    lasFileName : STRING
        DESCRIPTION. String representing the file path of a .las point cloud file.

    Returns
    -------
    lidar_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing coordinates and attributes of the lidar point cloud.
    
    '''
    if lasFileName.endswith('.las'):
        las = laspy.read(lasFileName)
        #point_format = las.point_format
        lidar_points = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
        lidar_df = pd.DataFrame(lidar_points)
        lidar_df[0] = lidar_df[0]/100
        lidar_df[1] = lidar_df[1]/100
        lidar_df[2] = lidar_df[2]/100
        lidar_df.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns']
    else:
        print('not a las file')
    return lidar_df

#

def lasDFcanopy(lidar_df):
    '''
    
    Parameters
    ----------
    lidar_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing coordinates and attributes of the lidar point cloud.

    Returns
    -------
    lidar_canopy_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing coordinates and attributes of the lidar point cloud with one-of-one, and last of many returns removed.
        This is a simple filter to drop solid objects and retain sparse objects such as leaves, branches, parts of the tree canopy; 
        ...unintentionally may retain power lines, fire escapes. 
    
    '''
    lidar_canopy_df = lidar_df[( lidar_df['number_of_returns'] - lidar_df['return_number'] ) > 0 ]
    return lidar_canopy_df

#

def lasDFclip(lidar_df,xMin,xMax,yMin,yMax):
    '''
    
    Parameters
    ----------
    lidar_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing coordinates and attributes of a lidar point cloud.
    xMin : FLOAT
        DESCRIPTION. Smallest cartesian X coordinate in the state plane system.
    xMax : FLOAT
        DESCRIPTION. Largest cartesian X coordinate in the state plane system.
    yMin : FLOAT
        DESCRIPTION. Smallest cartesian Y coordinate in the state plane system.
    yMax : FLOAT
        DESCRIPTION. Largest cartesian Y coordinate in the state plane system.

    Returns
    -------
    lidar_canopy_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing coordinates and attributes of a lidar point cloud, trimmed to bounds.
    
    '''
    lidar_clip_df = lidar_df[ lidar_df['X'] >= xMin ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['X'] <= xMax ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['Y'] >= yMin ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['Y'] <= yMax ]
    return lidar_clip_df

#

def treeDFclip(tree_df,xMin,xMax,yMin,yMax):
    '''
    
    Parameters
    ----------
    tree_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing NYC street tree census.
    xMin : FLOAT
        DESCRIPTION. Smallest cartesian X coordinate in the state plane system.
    xMax : FLOAT
        DESCRIPTION. Largest cartesian X coordinate in the state plane system.
    yMin : FLOAT
        DESCRIPTION. Smallest cartesian Y coordinate in the state plane system.
    yMax : FLOAT
        DESCRIPTION. Largest cartesian Y coordinate in the state plane system.

    Returns
    -------
    tree_clip_df : Pandas Dataframe
        DESCRIPTION. Dataframe containing subset of the NYC street tree census, trimmed to bounds.
    
    '''
    tree_clip_df = tree_df[ tree_df['x_sp'] >= xMin ]
    tree_clip_df = tree_clip_df[ tree_clip_df['x_sp'] <= xMax ]
    tree_clip_df = tree_clip_df[ tree_clip_df['y_sp'] >= yMin ]
    tree_clip_df = tree_clip_df[ tree_clip_df['y_sp'] <= yMax ]
    #add a Z clip
    return tree_clip_df

#

def readGeoJSON(filepath):
    '''
    
    Parameters
    ----------
    filepath : STRING
        DESCRIPTION. String representing the file path of a GeoJSON file.

    Returns
    -------
    features : JSON object / Dictionary
        DESCRIPTION. GeoJSON objects with coordinates and attributes.
    
    '''
    with open(filepath) as f:
        features = json.load(f)["features"]                
    return features

#

def footprintPointsFromGeoJSON(feature):   
    '''
    
    Parameters
    ----------
    feature : JSON object / Dictionary
        DESCRIPTION. Portion of a GeoJSON objects with coordinates and attributes accessed through iteration.

    Returns
    -------
    features : List
        DESCRIPTION. A list of X,Y,Z coordinates for the roof of a building derived from a GeoJSON file.
    
    '''
    points = []
    height = feature["properties"]["heightroof"] 
    for polygonPart in feature["geometry"]["coordinates"]:
        for polygonSubPart in polygonPart:
            for coordinates in polygonSubPart:
                point = [coordinates[0],coordinates[1],height]
                points.append(point)                  
    return points, height

#

def convertCoords(x,y):
    '''
    Parameters
    ----------
    x : FLOAT
        DESCRIPTION. cartesian x coordinate in state plane coordinate system for NY, long island (EPSG 2263) 
    y : FLOAT
        DESCRIPTION. cartesian y coordinate in state plane coordinate system for NY, long island (EPSG 2263) 
    Returns
    -------
    lat : FLOAT
        DESCRIPTION. latitude in WGS 1984 (EPSG 4326) 
    lon : FLOAT
        DESCRIPTION. longitude in WGS 1984 (EPSG 4326)
    '''
    transformer = Transformer.from_crs("epsg:2263", "epsg:4326")
    lat, lon = transformer.transform(x, y)
    return lat, lon

#

def convertLatLon(lat,lon):
    '''
    Parameters
    ----------
    lat : FLOAT
        DESCRIPTION. latitude in WGS 1984 (EPSG 4326) 
    lon : FLOAT
        DESCRIPTION. longitude in WGS 1984 (EPSG 4326)
    
    Returns
    -------
    x : FLOAT
        DESCRIPTION. cartesian x coordinate in state plane coordinate system for NY, long island (EPSG 2263) 
    y : FLOAT
        DESCRIPTION. cartesian y coordinate in state plane coordinate system for NY, long island (EPSG 2263) 
    '''
    transformer = Transformer.from_crs( "epsg:4326", "epsg:2263" ) 
    x, y = transformer.transform(lat, lon)
    return x, y

#

def projectToGround(point,az,amp):
    '''
    Parameters
    ----------
    point : LIST
        DESCRIPTION. List containing X, Y, Z coordinates of a point
    az : FLOAT
        DESCRIPTION. azimuth angle of the sun
    amp : FLOAT
        DESCRIPTION. amplitude (altitude, zenith) angle of the sun
    
    Returns
    -------
    pointGroundX : FLOAT
        DESCRIPTION. X coordinate of the shadow cast by a point 
    pointGroundY : FLOAT
        DESCRIPTION. Y coordinate of the shadow cast by a point 
    pointGroundZ : FLOAT
        DESCRIPTION. Z coordinate of the shadow cast by a point 
    '''
    if type(point[2]) is float:
        sinAz = math.sin( math.radians( az + 180.0 ) )
        cosAz = math.cos( math.radians( az + 180.0 ) )
        tanAmp = math.tan( math.radians(amp) )
        pointGroundX = point[0] + ( ( point[2] / tanAmp ) *sinAz )
        pointGroundY = point[1] + ( ( point[2] / tanAmp ) *cosAz )
        pointGroundZ =  point[2] * 0
        return pointGroundX,pointGroundY,pointGroundZ
    # handle missing height value for building
    else: 
        return point[0],point[1],1.0

#

def projectToGroundX(point,az,amp):
    '''
    Parameters
    ----------
    point : LIST
        DESCRIPTION. List containing X, Y, Z coordinates of a point
    az : FLOAT
        DESCRIPTION. azimuth angle of the sun
    amp : FLOAT
        DESCRIPTION. amplitude (altitude, zenith) angle of the sun
    
    Returns
    -------
    pointGroundX : FLOAT
        DESCRIPTION. X coordinate of the shadow cast by a point 
        Tailored version of the above script so that it can set a single column value in a pandas dataframe without errors.
    '''
    sinAz = math.sin( math.radians( az + 180.0 ) )
    cosAz = math.cos( math.radians( az + 180.0 ) )
    tanAmp = math.tan( math.radians(amp) )
    pointGroundX = point[0] + ( ( point[2] / tanAmp ) * sinAz )   
    return pointGroundX


#

def projectToGroundY(point,az,amp):  
    '''
    Parameters
    ----------
    point : LIST
        DESCRIPTION. List containing X, Y, Z coordinates of a point
    az : FLOAT
        DESCRIPTION. azimuth angle of the sun
    amp : FLOAT
        DESCRIPTION. amplitude (altitude, zenith) angle of the sun
    
    Returns
    -------
    pointGroundX : FLOAT
        DESCRIPTION. Y coordinate of the shadow cast by a point 
        Tailored version of the above script so that it can set a single column value in a pandas dataframe without errors.
    '''
    sinAz = math.sin( math.radians( az + 180.0 ) )
    cosAz = math.cos( math.radians( az + 180.0 ) )
    tanAmp = math.tan( math.radians(amp) )
    pointGroundY = point[1] + ( ( point[2] / tanAmp ) * cosAz )
    return pointGroundY


#

def pointsForHull(points,az,amp):
    '''
    Parameters
    ----------
    point : LIST
        DESCRIPTION. List containing X, Y, Z coordinates of a point
    az : FLOAT
        DESCRIPTION. azimuth angle of the sun
    amp : FLOAT
        DESCRIPTION. amplitude (altitude, zenith) angle of the sun
    
    Returns
    -------
    pointGroundX : LIST
        DESCRIPTION. A list of points for a building including the vertices of a building footprint on the ground, and the shadow cast by its roof.
    '''
    groundPointList = []
    for point in points:
        #point[0],point[1] = convertLatLon(point[1],point[0])
        groundPointList.append([point[0],point[1]])
        groundPoint = projectToGround(point,az,amp)
        groundPointList.append([groundPoint[0],groundPoint[1]])    
    return groundPointList

#

def pointsForBufferedHull(points):
    '''
    Parameters
    ----------
    points : LIST
        DESCRIPTION. List containing sublists of X,Y,Z coordinates from a GeoJSON
    
    Returns
    -------
    groundPointList : LIST
        DESCRIPTION. List containing sublists of X,Y coordinates from a GeoJSON
    '''
    groundPointList = []
    for point in points:
        #print(point)
        #point[0],point[1] = convertLatLon(point[1],point[0])
        #print(point)
        groundPointList.append([point[0],point[1]])   
    return groundPointList

#

def convexHull2D(points):
    '''
    Parameters
    ----------
    points : LIST
        DESCRIPTION. List containing sublists of X,Y coordinates
    
    Returns
    -------
    groundPointList : Hull object
        DESCRIPTION. Scipy object representing the convex hull containing points fed to it, for example the shadow (including footprint) of a building.
    '''
    points = np.array(points)
    hull = ConvexHull(points)
    return hull

#

def inBuilding(points, hull):   
    '''
    Parameters
    ----------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane, representing which includes coordinates of shadow cast by 3D points. 
    groundPointList : Hull object
        DESCRIPTION. Scipy object representing the convex hull containing points fed to it, for example the shadow (including footprint) of a building.
    
    Returns
    -------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane inside a hull. 
        Used for checking if a point is likely to be a facade feature, for example a fire escape, so it can be dropped from the dataframe. 
    '''
    vertexList = (hull.vertices).tolist()
    polygonPoints = []
    for index in vertexList:
        polygonPoints.append(hull.points[index])
    path = mpltPath.Path(polygonPoints)
    pointsIn = points[['X','Y']]
    points['temp'] = path.contains_points(pointsIn) 
    points['inBuilding'] = np.where( (points['inBuilding'] == 1) | (points['temp'] == 1),1,0 )
    return points

#

def inShadow(points, hull):    
    '''
    Parameters
    ----------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane, representing which includes coordinates of shadow cast by 3D points. 
    groundPointList : Hull object
        DESCRIPTION. Scipy object representing the convex hull containing points fed to it, for example the shadow (including footprint) of a building.
    
    Returns
    -------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane, representing which includes coordinates of shadow cast by 3D points. 
        Adds flag for falling inside or outside the hull of a building, representing if a point is being shaded by a building. 
        Supercedes all other conditions/flags.
        The X,Y  point must fall inside the hull of a building's footprint + shadow, both "in the air" and projected onto the ground. 
    '''
    vertexList = (hull.vertices).tolist()
    polygonPoints = []
    for index in vertexList:
        polygonPoints.append(hull.points[index])
    path = mpltPath.Path(polygonPoints)
    pointsIn = points[['X','Y']]
    pointsInGround = points[['groundX','groundY']]
    points['temp'] = path.contains_points(pointsIn) * path.contains_points(pointsInGround)
    points['inShade'] = np.where( (points['inShade'] == 1) | (points['temp'] == 1),1,0 )
    return points

#

def inFacade(points, hull):
    '''
    Parameters
    ----------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane, representing which includes coordinates of shadow cast by 3D points. 
    groundPointList : Hull object
        DESCRIPTION. Scipy object representing the convex hull containing points fed to it, for example the shadow (including footprint) of a building.
    
    Returns
    -------
    points : Pandas Dataframe
        DESCRIPTION. Points of a point cloud projected on to the ground plane, representing which includes coordinates of shadow cast by 3D points. 
        Adds flag for falling inside or outside the hull of a building, representing if a point is shading a facade. 
        Defers to the "in shadow" condition/flag.
    '''
    vertexList = (hull.vertices).tolist()
    polygonPoints = []
    for index in vertexList:
        polygonPoints.append(hull.points[index])
    path = mpltPath.Path(polygonPoints)
    pointsIn = points[['groundX','groundY']]
    points['temp'] = path.contains_points(pointsIn)
    points['inFacade'] = np.where( (points['inFacade'] == 1) | (points['temp'] == 1),1,0 )
    return points        


#

def trimGeoJSON(features,xMin,xMax,yMin,yMax,latLon):
    '''
    
    Parameters
    ----------
    features : LIST
        DESCRIPTION. GeoJSON polygons.
    xMin : FLOAT
        DESCRIPTION. Smallest cartesian X coordinate in the state plane system.
    xMax : FLOAT
        DESCRIPTION. Largest cartesian X coordinate in the state plane system.
    yMin : FLOAT
        DESCRIPTION. Smallest cartesian Y coordinate in the state plane system.
    yMax : FLOAT
        DESCRIPTION. Largest cartesian Y coordinate in the state plane system.
    yMax : STRING
        DESCRIPTION. Flag to trigger converting to state plane if provided coordinates are lat/lon. 'latLon' triggers reprojection.

    Returns
    -------
    features2 : LIST
        DESCRIPTION. Polygon features whose centroids fell inside the bounding box.
    
    '''
    features2 = []
    
    for feature in features[:]:
        buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
        xs = []
        ys = []
        for buildingPoint in buildingPoints:
            xs.append(buildingPoint[0])
            ys.append(buildingPoint[1])
        # average to find centroid of polygon
        xCenter = sum(xs)/len(xs)
        yCenter = sum(ys)/len(ys)
        
        if latLon == 'latLon':
            xCenter,yCenter = convertLatLon(yCenter,xCenter)
        else:
            xCenter,yCenter = xCenter,yCenter
        
        if xCenter > xMin and xCenter < xMax and yCenter > yMin and yCenter < yMax:
            features2.append(feature)
        else:
            continue
        
    return features2


#

def removeBuildingsFromLas(buildingsBufferedPath,lasdf):
    '''
    Parameters
    ----------
    buildingsBufferedPath : STRING
        DESCRIPTION. File path to a GeoJSON containing buffered building footprints.
    lasdf : Pandas Dataframe
        DESCRIPTION. Dataframe containing las point cloud data.
    
    Returns
    -------
    lasBuildings : Pandas Dataframe
        DESCRIPTION. Las point cloud dataframe that represent building features.
    lasdf : Pandas Dataframe
        DESCRIPTION. Dataframe containing las point cloud data with building features excluded.
    '''
    #buffered buildings currently use state plane coordinates for their vertices 
    featuresBuffered = readGeoJSON(buildingsBufferedPath)

    for feature in featuresBuffered:
        buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
        buildingPoints = pointsForBufferedHull(buildingPoints)
        buildingHull = convexHull2D(buildingPoints)
        lasdf = inBuilding(lasdf,buildingHull)
        
    lasBuildings = lasdf[lasdf['inBuilding'] == 1]
    lasdf = lasdf[lasdf['inBuilding'] == 0]
    
    return lasBuildings, lasdf
    

#

def lasPreprocess(lasTileNumber):
    '''
    Parameters
    ----------
    buildingsBufferedPath : INT
        DESCRIPTION. Number identifier of a lidar tile.
    
    Returns
    -------
    lasBuildings : Pandas Dataframe
        DESCRIPTION. Las point cloud dataframe that represent building features.
    lasdf : Pandas Dataframe
        DESCRIPTION. Dataframe containing las point cloud data with building features excluded.
    '''
    lasdf = processLas('las/{}.las'.format(lasTileNumber))
    lasdf = lasdf.dropna()
    groundElevation = lasdf[lasdf['class']==2]['Z'].mean()
    lasdf = lasDFcanopy(lasdf)
    lasdf['Z'] = lasdf['Z'] - groundElevation
    lasdf = lasdf[ lasdf['Z'] < 1000 ]
    lasdf['temp'] = 0
    lasdf['inBuilding'] = 0
    # requires a geojson file of building footprints that have already been buffered, and selected down to the buildings that fall inside the tile. 
    lasBuildings, lasdf =  removeBuildingsFromLas('buildings/buildingsTile{}buffered.geojson'.format(lasTileNumber),lasdf)
    return lasBuildings, lasdf

#

def lasProcess(iterator):
    '''
    Parameters
    ----------
    buildingsBufferedPath : LIST
        DESCRIPTION. A set of parameters in the sequence:
        [pointer to las dataframe, number for las tile, sun azimuth, sun amplitude, string representing datetime].
    
    Returns
    -------
    lasBuildings : Pandas Dataframe
        DESCRIPTION. Las point cloud dataframe that represent building features.
    lasdf : Pandas Dataframe
        DESCRIPTION. Dataframe containing las point cloud data with building features excluded.
    '''
    #wrapper function for multiprocessing
    #az here is geometric degrees (counterclockwise, north = 90) not compass heading degrees (clockwise, north = 0)
    lasdf = iterator[0]
    lasTileNumber = iterator[1]
    az = iterator[2]
    amp = iterator[3]
    dateTimeString = iterator[4]
    
    lasdf['groundX'] = lasdf.apply(lambda x: projectToGroundX([x['X'],x['Y'],x['Z']],az,amp) , axis=1)
    lasdf['groundY'] = lasdf.apply(lambda x: projectToGroundY([x['X'],x['Y'],x['Z']],az,amp) , axis=1)

    lasdf['temp'] = 0
    lasdf['inShade'] = 0

    features = readGeoJSON('buildings/buildingsTile{}.geojson'.format(lasTileNumber))

    hulls = []

    #check in shadow
    for feature in features:
        buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
        buildingPointsGround = pointsForHull(buildingPoints,az,amp)
        buildingHull = convexHull2D(buildingPointsGround)
        hulls.append(buildingHull)
        lasdf = inShadow(lasdf,buildingHull)

    lasInShade = lasdf[lasdf['inShade'] == 1]
    lasNotShade = lasdf[lasdf['inShade'] == 0]

    lasNotShade['temp'] = 0
    lasNotShade['inFacade'] = 0

    #check shading facade
    for buildingHull in hulls:
        lasNotShade = inFacade(lasNotShade,buildingHull)

    lasShadeFacade = lasNotShade[lasNotShade['inFacade'] == 1]
    lasShadeRoad = lasNotShade[lasNotShade['inFacade'] == 0]
    
    lasShadeRoad = lasShadeRoad[['X','Y','Z','intens','groundX','groundY']]
    lasInShade = lasInShade[['X','Y','Z','intens','groundX','groundY']]
    lasShadeFacade = lasShadeFacade[['X','Y','Z','intens','groundX','groundY']]
    
    lasShadeRoad.to_csv('shadeShadingShadedDataframes/{}_tile{}_shadingGround.csv'.format(dateTimeString,lasTileNumber))
    lasInShade.to_csv('shadeShadingShadedDataframes/{}_tile{}_inShade.csv'.format(dateTimeString,lasTileNumber))
    lasShadeFacade.to_csv('shadeShadingShadedDataframes/{}_tile{}_shadingFacade.csv'.format(dateTimeString,lasTileNumber))


############################################################################################################################################################################



startTime = str(datetime.datetime.now())


#


lasdf25252buildingPoints,lasdf25252 = lasPreprocess('25252')
lasdf32187buildingPoints,lasdf32187 = lasPreprocess('32187')
lasdf987180buildingPoints,lasdf987180 = lasPreprocess('987180')

print('Preprocessing done')

#

# used to find sun angles, this could probably be done programatically: https://gml.noaa.gov/grad/solcalc/azel.html

# these iterator combos could also probably be generated programatically...
iterators = [
    
    [lasdf25252,'25252',90,38,'2022_06_21_0800'], #Summer Solstice: '2022_06_21_0800'
    [lasdf25252,'25252',101,49,'2022_06_21_0900'],  #Summer Solstice: 2022 06 21, 0900
    [lasdf25252,'25252',116,60,'2022_06_21_1000'],  #Summer Solstice: 2022 06 21, 1000
    [lasdf25252,'25252',140,69,'2022_06_21_1100'],  #Summer Solstice: 2022 06 21, 1100
    [lasdf25252,'25252',182,73,'2022_06_21_1200'],  #Summer Solstice: 2022 06 21, 1200
    [lasdf25252,'25252',222,68,'2022_06_21_1300'],  #Summer Solstice: 2022 06 21, 1300
    [lasdf25252,'25252',245,59,'2022_06_21_1400'],  #Summer Solstice: 2022 06 21, 1400
    [lasdf25252,'25252',260,48,'2022_06_21_1500'],  #Summer Solstice: 2022 06 21, 1500
    [lasdf25252,'25252',270,37,'2022_06_21_1600'],  #Summer Solstice: 2022 06 21, 1600
    
    [lasdf25252,'25252',97,33,'2022_08_07_0800'],  # 2022 08 07, 0800
    [lasdf25252,'25252',108,44,'2022_08_07_0900'],  # 2022 08 07, 0900
    [lasdf25252,'25252',124,54,'2022_08_07_1000'],  # 2022 08 07, 1000
    [lasdf25252,'25252',147,62,'2022_08_07_1100'],  # 2022 08 07, 1100
    [lasdf25252,'25252',179,66,'2022_08_07_1200'],  # 2022 08 07, 1200
    [lasdf25252,'25252',211,63,'2022_08_07_1300'],  # 2022 08 07, 1300
    [lasdf25252,'25252',235,55,'2022_08_07_1400'],  # 2022 08 07, 1400
    [lasdf25252,'25252',251,45,'2022_08_07_1500'],  # 2022 08 07, 1500
    [lasdf25252,'25252',263,33,'2022_08_07_1600'],  # 2022 08 07, 1600
    
    [lasdf25252,'25252',113,24,'2022_09_22_0800'], #Autumn Equinox: 2022 09 22, 0800
    [lasdf25252,'25252',126,34,'2022_09_22_0900'],  #Autumn Equinox: 2022 09 22, 0900
    [lasdf25252,'25252',142,43,'2022_09_22_1000'],  #Autumn Equinox: 2022 09 22, 1000
    [lasdf25252,'25252',162,48,'2022_09_22_1100'],  #Autumn Equinox: 2022 09 22, 1100
    [lasdf25252,'25252',184,49,'2022_09_22_1200'],  #Autumn Equinox: 2022 09 22, 1200
    [lasdf25252,'25252',206,46,'2022_09_22_1300'],  #Autumn Equinox: 2022 09 22, 1300
    [lasdf25252,'25252',225,40,'2022_09_22_1400'],  #Autumn Equinox: 2022 09 22, 1400
    [lasdf25252,'25252',239,31,'2022_09_22_1500'],  #Autumn Equinox: 2022 09 22, 1500
    [lasdf25252,'25252',252,20,'2022_09_22_1600'],  #Autumn Equinox: 2022 09 22, 1600
    
    [lasdf25252,'25252',126,14,'2022_11_07_0800'],  # 2022 11 07, 0800
    [lasdf25252,'25252',138,22,'2022_11_07_0900'],  # 2022 11 07, 0900
    [lasdf25252,'25252',153,28,'2022_11_07_1000'],  # 2022 11 07, 1000
    [lasdf25252,'25252',169,32,'2022_11_07_1100'],  # 2022 11 07, 1100
    [lasdf25252,'25252',186,33,'2022_11_07_1200'],  # 2022 11 07, 1200
    [lasdf25252,'25252',202,30,'2022_11_07_1300'],  # 2022 11 07, 1300
    [lasdf25252,'25252',217,24,'2022_11_07_1400'],  # 2022 11 07, 1400
    [lasdf25252,'25252',230,16,'2022_11_07_1500'],  # 2022 11 07, 1500
    [lasdf25252,'25252',241,7,'2022_11_07_1600'],  # 2022 11 07, 1600
    
    [lasdf25252,'25252',128,6,'2022_12_21_0800'], #Winter Solstice: 2022 12 21, 0800
    [lasdf25252,'25252',139,14,'2022_12_21_0900'],  #Winter Solstice: 2022 12 21, 0900
    [lasdf25252,'25252',152,21,'2022_12_21_1000'],  #Winter Solstice: 2022 12 21, 1000
    [lasdf25252,'25252',166,25,'2022_12_21_1100'],  #Winter Solstice: 2022 12 21, 1100
    [lasdf25252,'25252',181,26,'2022_12_21_1200'],  #Winter Solstice: 2022 12 21, 1200
    [lasdf25252,'25252',197,24,'2022_12_21_1300'],  #Winter Solstice: 2022 12 21, 1300
    [lasdf25252,'25252',211,20,'2022_12_21_1400'],  #Winter Solstice: 2022 12 21, 1400
    [lasdf25252,'25252',223,13,'2022_12_21_1500'],  #Winter Solstice: 2022 12 21, 1500
    [lasdf25252,'25252',234,4,'2022_12_21_1600'],  #Winter Solstice: 2022 12 21, 1600
    
    #
    
    [lasdf32187,'32187',90,38,'2022_06_21_0800'], #Summer Solstice: 2022 06 21, 0800
    [lasdf32187,'32187',101,49,'2022_06_21_0900'],  #Summer Solstice: 2022 06 21, 0900
    [lasdf32187,'32187',116,60,'2022_06_21_1000'],  #Summer Solstice: 2022 06 21, 1000
    [lasdf32187,'32187',140,69,'2022_06_21_1100'],  #Summer Solstice: 2022 06 21, 1100
    [lasdf32187,'32187',182,73,'2022_06_21_1200'],  #Summer Solstice: 2022 06 21, 1200
    [lasdf32187,'32187',222,68,'2022_06_21_1300'],  #Summer Solstice: 2022 06 21, 1300
    [lasdf32187,'32187',245,59,'2022_06_21_1400'],  #Summer Solstice: 2022 06 21, 1400
    [lasdf32187,'32187',260,48,'2022_06_21_1500'],  #Summer Solstice: 2022 06 21, 1500
    [lasdf32187,'32187',270,37,'2022_06_21_1600'],  #Summer Solstice: 2022 06 21, 1600
    
    [lasdf32187,'32187',97,33,'2022_08_07_0800'],  # 2022 08 07, 0800
    [lasdf32187,'32187',108,44,'2022_08_07_0900'],  # 2022 08 07, 0900
    [lasdf32187,'32187',124,54,'2022_08_07_1000'],  # 2022 08 07, 1000
    [lasdf32187,'32187',147,62,'2022_08_07_1100'],  # 2022 08 07, 1100
    [lasdf32187,'32187',179,66,'2022_08_07_1200'],  # 2022 08 07, 1200
    [lasdf32187,'32187',211,63,'2022_08_07_1300'],  # 2022 08 07, 1300
    [lasdf32187,'32187',235,55,'2022_08_07_1400'],  # 2022 08 07, 1400
    [lasdf32187,'32187',251,45,'2022_08_07_1500'],  # 2022 08 07, 1500
    [lasdf32187,'32187',263,33,'2022_08_07_1600'],  # 2022 08 07, 1600
    
    [lasdf32187,'32187',113,24,'2022_09_22_0800'], #Autumn Equinox: 2022 09 22, 0800
    [lasdf32187,'32187',126,34,'2022_09_22_0900'],  #Autumn Equinox: 2022 09 22, 0900
    [lasdf32187,'32187',142,43,'2022_09_22_1000'],  #Autumn Equinox: 2022 09 22, 1000
    [lasdf32187,'32187',162,48,'2022_09_22_1100'],  #Autumn Equinox: 2022 09 22, 1100
    [lasdf32187,'32187',184,49,'2022_09_22_1200'],  #Autumn Equinox: 2022 09 22, 1200
    [lasdf32187,'32187',206,46,'2022_09_22_1300'],  #Autumn Equinox: 2022 09 22, 1300
    [lasdf32187,'32187',225,40,'2022_09_22_1400'],  #Autumn Equinox: 2022 09 22, 1400
    [lasdf32187,'32187',239,31,'2022_09_22_1500'],  #Autumn Equinox: 2022 09 22, 1500
    [lasdf32187,'32187',252,20,'2022_09_22_1600'],  #Autumn Equinox: 2022 09 22, 1600
    
    [lasdf32187,'32187',126,14,'2022_11_07_0800'],  # 2022 11 07, 0800
    [lasdf32187,'32187',138,22,'2022_11_07_0900'],  # 2022 11 07, 0900
    [lasdf32187,'32187',153,28,'2022_11_07_1000'],  # 2022 11 07, 1000
    [lasdf32187,'32187',169,32,'2022_11_07_1100'],  # 2022 11 07, 1100
    [lasdf32187,'32187',186,33,'2022_11_07_1200'],  # 2022 11 07, 1200
    [lasdf32187,'32187',202,30,'2022_11_07_1300'],  # 2022 11 07, 1300
    [lasdf32187,'32187',217,24,'2022_11_07_1400'],  # 2022 11 07, 1400
    [lasdf32187,'32187',230,16,'2022_11_07_1500'],  # 2022 11 07, 1500
    [lasdf32187,'32187',241,7,'2022_11_07_1600'],  # 2022 11 07, 1600
    
    [lasdf32187,'32187',128,6,'2022_12_21_0800'], #Winter Solstice: 2022 12 21, 0800
    [lasdf32187,'32187',139,14,'2022_12_21_0900'],  #Winter Solstice: 2022 12 21, 0900
    [lasdf32187,'32187',152,21,'2022_12_21_1000'],  #Winter Solstice: 2022 12 21, 1000
    [lasdf32187,'32187',166,25,'2022_12_21_1100'],  #Winter Solstice: 2022 12 21, 1100
    [lasdf32187,'32187',181,26,'2022_12_21_1200'],  #Winter Solstice: 2022 12 21, 1200
    [lasdf32187,'32187',197,24,'2022_12_21_1300'],  #Winter Solstice: 2022 12 21, 1300
    [lasdf32187,'32187',211,20,'2022_12_21_1400'],  #Winter Solstice: 2022 12 21, 1400
    [lasdf32187,'32187',223,13,'2022_12_21_1500'],  #Winter Solstice: 2022 12 21, 1500
    [lasdf32187,'32187',234,4,'2022_12_21_1600'],  #Winter Solstice: 2022 12 21, 1600
    
    #
    
    [lasdf987180,'987180',90,38,'2022_06_21_0800'], #Summer Solstice: 2022 06 21, 0800
    [lasdf987180,'987180',101,49,'2022_06_21_0900'],  #Summer Solstice: 2022 06 21, 0900
    [lasdf987180,'987180',116,60,'2022_06_21_1000'],  #Summer Solstice: 2022 06 21, 1000
    [lasdf987180,'987180',140,69,'2022_06_21_1100'],  #Summer Solstice: 2022 06 21, 1100
    [lasdf987180,'987180',182,73,'2022_06_21_1200'],  #Summer Solstice: 2022 06 21, 1200
    [lasdf987180,'987180',222,68,'2022_06_21_1300'],  #Summer Solstice: 2022 06 21, 1300
    [lasdf987180,'987180',245,59,'2022_06_21_1400'],  #Summer Solstice: 2022 06 21, 1400
    [lasdf987180,'987180',260,48,'2022_06_21_1500'],  #Summer Solstice: 2022 06 21, 1500
    [lasdf987180,'987180',270,37,'2022_06_21_1600'],  #Summer Solstice: 2022 06 21, 1600
    
    [lasdf987180,'987180',97,33,'2022_08_07_0800'],  # 2022 08 07, 0800
    [lasdf987180,'987180',108,44,'2022_08_07_0900'],  # 2022 08 07, 0900
    [lasdf987180,'987180',124,54,'2022_08_07_1000'],  # 2022 08 07, 1000
    [lasdf987180,'987180',147,62,'2022_08_07_1100'],  # 2022 08 07, 1100
    [lasdf987180,'987180',179,66,'2022_08_07_1200'],  # 2022 08 07, 1200
    [lasdf987180,'987180',211,63,'2022_08_07_1300'],  # 2022 08 07, 1300
    [lasdf987180,'987180',235,55,'2022_08_07_1400'],  # 2022 08 07, 1400
    [lasdf987180,'987180',251,45,'2022_08_07_1500'],  # 2022 08 07, 1500
    [lasdf987180,'987180',263,33,'2022_08_07_1600'],  # 2022 08 07, 1600
    
    [lasdf987180,'987180',113,24,'2022_09_22_0800'], #Autumn Equinox: 2022 09 22, 0800
    [lasdf987180,'987180',126,34,'2022_09_22_0900'],  #Autumn Equinox: 2022 09 22, 0900
    [lasdf987180,'987180',142,43,'2022_09_22_1000'],  #Autumn Equinox: 2022 09 22, 1000
    [lasdf987180,'987180',162,48,'2022_09_22_1100'],  #Autumn Equinox: 2022 09 22, 1100
    [lasdf987180,'987180',184,49,'2022_09_22_1200'],  #Autumn Equinox: 2022 09 22, 1200
    [lasdf987180,'987180',206,46,'2022_09_22_1300'],  #Autumn Equinox: 2022 09 22, 1300
    [lasdf987180,'987180',225,40,'2022_09_22_1400'],  #Autumn Equinox: 2022 09 22, 1400
    [lasdf987180,'987180',239,31,'2022_09_22_1500'],  #Autumn Equinox: 2022 09 22, 1500
    [lasdf987180,'987180',252,20,'2022_09_22_1600'],  #Autumn Equinox: 2022 09 22, 1600
    
    [lasdf987180,'987180',126,14,'2022_11_07_0800'],  # 2022 11 07, 0800
    [lasdf987180,'987180',138,22,'2022_11_07_0900'],  # 2022 11 07, 0900
    [lasdf987180,'987180',153,28,'2022_11_07_1000'],  # 2022 11 07, 1000
    [lasdf987180,'987180',169,32,'2022_11_07_1100'],  # 2022 11 07, 1100
    [lasdf987180,'987180',186,33,'2022_11_07_1200'],  # 2022 11 07, 1200
    [lasdf987180,'987180',202,30,'2022_11_07_1300'],  # 2022 11 07, 1300
    [lasdf987180,'987180',217,24,'2022_11_07_1400'],  # 2022 11 07, 1400
    [lasdf987180,'987180',230,16,'2022_11_07_1500'],  # 2022 11 07, 1500
    [lasdf987180,'987180',241,7,'2022_11_07_1600'],  # 2022 11 07, 1600
    
    [lasdf987180,'987180',128,6,'2022_12_21_0800'], #Winter Solstice: 2022 12 21, 0800
    [lasdf987180,'987180',139,14,'2022_12_21_0900'],  #Winter Solstice: 2022 12 21, 0900
    [lasdf987180,'987180',152,21,'2022_12_21_1000'],  #Winter Solstice: 2022 12 21, 1000
    [lasdf987180,'987180',166,25,'2022_12_21_1100'],  #Winter Solstice: 2022 12 21, 1100
    [lasdf987180,'987180',181,26,'2022_12_21_1200'],  #Winter Solstice: 2022 12 21, 1200
    [lasdf987180,'987180',197,24,'2022_12_21_1300'],  #Winter Solstice: 2022 12 21, 1300
    [lasdf987180,'987180',211,20,'2022_12_21_1400'],  #Winter Solstice: 2022 12 21, 1400
    [lasdf987180,'987180',223,13,'2022_12_21_1500'],  #Winter Solstice: 2022 12 21, 1500
    [lasdf987180,'987180',234,4,'2022_12_21_1600']  #Winter Solstice: 2022 12 21, 1600
    
    ]


if __name__ == '__main__':
    with Pool() as p:
        p.map(lasProcess, iterators)



print('Started processing at ' + startTime)
endTime = str(datetime.datetime.now())
print('Finished processing at ' + endTime)




# #############################################################

# #3d plot 

# treeLat = 40.68449261
# treeLon = -73.98669463

# treeX, treeY = convertLatLon(treeLat,treeLon)

# plt.clf()
# plt.close()

# import matplotlib.path as mpltPath
# import matplotlib as mpl
# from mpl_toolkits.mplot3d import Axes3D

# fig = plt.figure(figsize=(3,3), dpi=600, constrained_layout=True)

# ax1 = fig.add_subplot(1, 1, 1, projection='3d') ############

# canopy_radius = 25

# lasBuildings['X'] = lasBuildings['X'] - treeX
# lasBuildings['Y'] = lasBuildings['Y'] - treeY
# lasBuildings = lasBuildings[ ( ( (lasBuildings['X'] )**2 + ( lasBuildings['Y'] )**2 ) ** 0.5 ) < canopy_radius*3 ]

# lasShadeRoad['X'] = lasShadeRoad['X'] - treeX
# lasShadeRoad['Y'] = lasShadeRoad['Y'] - treeY
# lasShadeRoad = lasShadeRoad[ ( ( ( lasShadeRoad['X'] )**2 + ( lasShadeRoad['Y'] )**2 ) ** 0.5 ) < canopy_radius ]


# lasInShade['X'] = lasInShade['X'] - treeX
# lasInShade['Y'] = lasInShade['Y'] - treeY
# lasInShade = lasInShade[ ( ( ( lasInShade['X'] )**2 + ( lasInShade['Y'] )**2 ) ** 0.5 ) < canopy_radius ]

# lasShadeFacade['X'] = lasShadeFacade['X'] - treeX
# lasShadeFacade['Y'] = lasShadeFacade['Y'] - treeY
# lasShadeFacade = lasShadeFacade[ ( ( ( lasShadeFacade['X'] )**2 + ( lasShadeFacade['Y'] )**2 ) ** 0.5 ) < canopy_radius ]

# xs = []
# ys = []
# zs = []

# for x in range(-canopy_radius,canopy_radius+1):
#     for y in range(-canopy_radius,canopy_radius+1):
#         xs.append(x)
#         ys.append(y)
#         zs.append(0.1)
#         xs.append(x)
#         ys.append(y)
#         zs.append(canopy_radius*2)

# ax1.scatter3D(xs, ys, zs, color='whitesmoke', zdir='z', s=0.01, marker='+', depthshade=True)
# #ax1.scatter3D(lasBuildings['X'], lasBuildings['Y'], lasBuildings['Z'], color='lightgray', zdir='z', s=0.01, marker='o', depthshade=True)
# ax1.scatter3D(lasShadeRoad['X'], lasShadeRoad['Y'], lasShadeRoad['Z'],color='seagreen', zdir='z', s=0.02, marker='o', depthshade=True)
# ax1.scatter3D(lasInShade['X'], lasInShade['Y'], lasInShade['Z'],color='black', zdir='z', s=0.02,marker='o', depthshade=True)
# ax1.scatter3D(lasShadeFacade['X'], lasShadeFacade['Y'], lasShadeFacade['Z'],color='indianred', zdir='z', s=0.02, marker='o', depthshade=True)


# ax1.view_init(90, 0)

# ax1.set_xticks([])
# ax1.set_yticks([])
# ax1.set_zticks([])
# #ax1.grid(False)
# ax1.set_axis_off()

# ax1.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax1.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax1.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

# ax1.set_xlim3d(-canopy_radius, canopy_radius)
# ax1.set_ylim3d(-canopy_radius, canopy_radius)
# ax1.set_zlim3d(0, canopy_radius*2)

# #fig.subplots_adjust(bottom=-0.1, top=1.1, left=-0.1, right=1.1, wspace=-0.1, hspace=-0.1)

# fig.savefig('3dtree.png')

# plt.show()

# #plt.close()













