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
        point[0],point[1] = convertLatLon(point[1],point[0])
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



############################################################################################################################################################################


plt.clf()

startTime = str(datetime.datetime.now())

xMin = 988200
xMax = 988800
yMin = 188800
yMax = 189200

# treedf = pd.read_csv('csv/2015StreetTreesCensus_TREES.csv')
# treedf = treeDFclip(treedf,xMin,xMax,yMin,yMax)
# print(treedf)

lasdf = processLas('las/987187.las')
lasdf = lasdf.dropna()
lasdf = lasDFclip(lasdf,xMin,xMax,yMin,yMax)

groundElevation = lasdf[lasdf['class']==2]['Z'].mean()

lasdf = lasDFcanopy(lasdf)

lasdf['Z'] = lasdf['Z'] - groundElevation

lasdf = lasdf[ lasdf['Z'] < 1000 ]

#az here is geometric degrees (counterclockwise, north = 90) not compass heading degrees (clockwise, north = 0)
az = 179.0
amp = 45.0

lasdf['groundX'] = lasdf.apply(lambda x: projectToGroundX([x['X'],x['Y'],x['Z']],az,amp) , axis=1)
lasdf['groundY'] = lasdf.apply(lambda x: projectToGroundY([x['X'],x['Y'],x['Z']],az,amp) , axis=1)

print(lasdf)

lasdf['temp'] = 0
lasdf['inBuilding'] = 0

#buffered buildings currently use state plane coordinates for their vertices 
featuresBuffered = readGeoJSON('buildings/buildingsTile987187buffered.geojson')
    
featuresBuffered = trimGeoJSON(featuresBuffered,xMin,xMax,yMin,yMax,'statePlane')

i=1
for feature in featuresBuffered:
    #print(i)
    buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
    buildingPoints = pointsForBufferedHull(buildingPoints)
    buildingHull = convexHull2D(buildingPoints)
    lasdf = inBuilding(lasdf,buildingHull)
    i+=1
    
lasBuildings = lasdf[lasdf['inBuilding'] == 1]
lasdf = lasdf[lasdf['inBuilding'] == 0]

print(lasdf)

plt.scatter(lasBuildings['X'],lasBuildings['Y'],marker="+",s=1,c=lasBuildings['Z'],cmap='binary')

lasdf['temp'] = 0
lasdf['inShade'] = 0


features = readGeoJSON('buildings/buildingsTile987187.geojson')

features = trimGeoJSON(features,xMin,xMax,yMin,yMax,'latLon')

hulls = []

#check in shadow
i=1
for feature in features:
    #print(i)
    buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
    buildingPointsGround = pointsForHull(buildingPoints,az,amp)
    buildingHull = convexHull2D(buildingPointsGround)
    hulls.append(buildingHull)
    lasdf = inShadow(lasdf,buildingHull)
    i+=1
    
print(lasdf)

lasInShade = lasdf[lasdf['inShade'] == 1]
lasNotShade = lasdf[lasdf['inShade'] == 0]

lasNotShade['temp'] = 0
lasNotShade['inFacade'] = 0

#check shading facade
i=1
for buildingHull in hulls:
    #print(i)
    #buildingPoints,buildingHeight = footprintPointsFromGeoJSON(feature)
    #buildingPointsGround = pointsForHull(buildingPoints,az,amp)
    #buildingHull = convexHull2D(buildingPointsGround)
    lasNotShade = inFacade(lasNotShade,buildingHull)
    i+=1

lasShadeFacade = lasNotShade[lasNotShade['inFacade'] == 1]
lasShadeRoad = lasNotShade[lasNotShade['inFacade'] == 0]

print('las shading road')
print(lasShadeRoad)
print('las in shade')
print(lasInShade)
print('las shading facade')
print(lasShadeFacade)

plt.scatter(lasShadeRoad['X'],lasShadeRoad['Y'],marker="o",s=4,c=lasShadeRoad['Z'],cmap='summer')
plt.scatter(lasInShade['X'],lasInShade['Y'],marker="o",s=4,c=lasInShade['Z'],cmap='bone')
plt.scatter(lasShadeFacade['X'],lasShadeFacade['Y'],marker="o",s=4,c=lasShadeFacade['Z'],cmap='pink')

plt.show()



print('Started processing at ' + startTime)
endTime = str(datetime.datetime.now())
print('Finished processing at ' + endTime)




# #############################################################

# #3d plot 

# plt.close()

# import matplotlib.path as mpltPath
# import matplotlib as mpl
# from mpl_toolkits.mplot3d import Axes3D

# fig = plt.figure(figsize=(3,3), dpi=600, constrained_layout=True)

# ax1 = fig.add_subplot(1, 1, 1, projection='3d') ############

# xMin = 996675
# xMax = 996925
# yMin = 238775
# yMax = 239225

# inPointsNorthFalse = lasDFclip(inPointsNorthFalse,xMin,xMax,yMin,yMax)
# inPointsNorthTrue = lasDFclip(inPointsNorthTrue,xMin,xMax,yMin,yMax)
# inPointsSouthTrue = lasDFclip(inPointsSouthTrue,xMin,xMax,yMin,yMax)

# ax1.scatter3D(inPointsNorthFalse['X'], inPointsNorthFalse['Y'], inPointsNorthFalse['Z'],color='green', zdir='z', s=0.01, marker='+', depthshade=True)
# ax1.scatter3D(inPointsNorthTrue['X'], inPointsNorthTrue['Y'], inPointsNorthTrue['Z'],color='blue', zdir='z', s=0.1,marker='+', depthshade=True)
# ax1.scatter3D(inPointsSouthTrue['X'], inPointsSouthTrue['Y'], inPointsSouthTrue['Z'],color='red', zdir='z', s=0.1, marker='+', depthshade=True)
# #ax1.scatter3D(xyzDF2['X'], xyzDF2['Y'], xyzDF2['Z'], zdir='z', s=0.2, c=xyzDF2['intens'], cmap='bone', marker='+', depthshade=True)
# #ax.plot_trisurf(lidar_df[0], lidar_df[1], lidar_df[2], color=[lidar_df[2],lidar_df[2],lidar_df[2]], linewidth=0.2, antialiased=True)

# ax1.view_init(0, -20)

# ax1.set_xticks([])
# ax1.set_yticks([])
# ax1.set_zticks([])
# ax1.grid(False)
# ax1.set_axis_off()

# ax1.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax1.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
# ax1.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

# # ax1.set_xlim3d(-35, 35)
# # ax1.set_ylim3d(-35, 35)
# ax1.set_zlim3d(0, 250)

# fig.subplots_adjust(bottom=-0.1, top=1.1, left=-0.1, right=1.1, wspace=-0.1, hspace=-0.1)

# fig.savefig('3dstreet.png')

# plt.show()

# #plt.close()













