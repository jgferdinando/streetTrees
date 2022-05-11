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
    lidar_canopy_df = lidar_df[( lidar_df['number_of_returns'] - lidar_df['return_number'] ) > 0 ]
    return lidar_canopy_df

#

def lasDFclip(lidar_df,xMin,xMax,yMin,yMax):
    lidar_clip_df = lidar_df[ lidar_df['X'] >= xMin ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['X'] <= xMax ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['Y'] >= yMin ]
    lidar_clip_df = lidar_clip_df[ lidar_clip_df['Y'] <= yMax ]
    return lidar_clip_df

#

def treeDFclip(tree_df,xMin,xMax,yMin,yMax):
    tree_clip_df = tree_df[ tree_df['x_sp'] >= xMin ]
    tree_clip_df = tree_clip_df[ tree_clip_df['x_sp'] <= xMax ]
    tree_clip_df = tree_clip_df[ tree_clip_df['y_sp'] >= yMin ]
    tree_clip_df = tree_clip_df[ tree_clip_df['y_sp'] <= yMax ]
    #add a Z clip
    return tree_clip_df

#

def readGeoJSON(filepath):
    with open(filepath) as f:
        features = json.load(f)["features"]                
    return features

#

def footprintPointsFromGeoJSON(feature):   
    points = []
    height = feature["properties"]["heightroof"] ################## verify this is the correct attribute name
    for polygonPart in feature["geometry"]["coordinates"]:
        for polygonSubPart in polygonPart:
            for coordinates in polygonSubPart:
                point = [coordinates[0],coordinates[1],height]
                points.append(point)                  
    return points, height

#

def convertCoords(x,y):
    transformer = Transformer.from_crs("epsg:2263", "epsg:4326")
    lat, lon = transformer.transform(x, y)
    return lat, lon

#

def convertLatLon(lat,lon):
    #translate from geojson CRS (NAD 1983) to .las CRS (UTM Zone 18N (meters))
    transformer = Transformer.from_crs( "epsg:4326", "epsg:2263" ) 
    x, y = transformer.transform(lat, lon)
    return x, y

#

def projectToGround(point,az,amp):
    if type(point[2]) is float:
        sinAz = math.sin( math.radians( az + 180.0 ) )
        cosAz = math.cos( math.radians( az + 180.0 ) )
        tanAmp = math.tan( math.radians(amp) )
        pointGroundX = point[0] + ( ( point[2] / tanAmp ) *sinAz )
        pointGroundY = point[1] + ( ( point[2] / tanAmp ) *cosAz )
        pointGroundZ =  point[2] * 0
        return pointGroundX,pointGroundY,pointGroundZ
    else: 
        print('bad Z')
        return point[0],point[1],1.0

#

def projectToGroundX(point,az,amp):
    sinAz = math.sin( math.radians( az + 180.0 ) )
    cosAz = math.cos( math.radians( az + 180.0 ) )
    tanAmp = math.tan( math.radians(amp) )
    pointGroundX = point[0] + ( ( point[2] / tanAmp ) * sinAz )   
    return pointGroundX


#

def projectToGroundY(point,az,amp):   
    sinAz = math.sin( math.radians( az + 180.0 ) )
    cosAz = math.cos( math.radians( az + 180.0 ) )
    tanAmp = math.tan( math.radians(amp) )
    pointGroundY = point[1] + ( ( point[2] / tanAmp ) * cosAz )
    return pointGroundY


#

def pointsForHull(points,az,amp):
    groundPointList = []
    for point in points:
        #point[0],point[1] = convertLatLon(point[1],point[0])
        groundPointList.append([point[0],point[1]])
        groundPoint = projectToGround(point,az,amp)
        groundPointList.append([groundPoint[0],groundPoint[1]])    
    return groundPointList

#

def pointsForBufferedHull(points):
    groundPointList = []
    for point in points:
        #print(point)
        #point[0],point[1] = convertLatLon(point[1],point[0])
        #print(point)
        groundPointList.append([point[0],point[1]])   
    return groundPointList

#

def convexHull2D(points):
    points = np.array(points)
    hull = ConvexHull(points)
    return hull

#

def inBuilding(points, hull):      
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
    
    features2 = []
    
    for feature in features[:]:
        buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
        xs = []
        ys = []
        for buildingPoint in buildingPoints:
            xs.append(buildingPoint[0])
            ys.append(buildingPoint[1])
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

def removeBuildingsFromLas(buildingsBufferedPaath,lasdf):
    #buffered buildings currently use state plane coordinates for their vertices 
    featuresBuffered = readGeoJSON(buildingsBufferedPaath)

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
    lasdf = processLas('las/{}.las'.format(lasTileNumber))
    lasdf = lasdf.dropna()

    groundElevation = lasdf[lasdf['class']==2]['Z'].mean()

    lasdf = lasDFcanopy(lasdf)

    lasdf['Z'] = lasdf['Z'] - groundElevation

    lasdf = lasdf[ lasdf['Z'] < 1000 ]

    lasdf['temp'] = 0
    lasdf['inBuilding'] = 0
        
    lasBuildings, lasdf =  removeBuildingsFromLas('buildings/buildingsTile{}buffered.geojson'.format(lasTileNumber),lasdf)
    
    return lasBuildings, lasdf

def lasProcess(iterator):
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

# https://gml.noaa.gov/grad/solcalc/azel.html

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













