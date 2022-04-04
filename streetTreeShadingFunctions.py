#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 24 08:07:59 2022

@author: joe
"""

#

# read las file into a pandas dataframe

def processLas(lasFileName):
    
    import laspy
    import numpy as np
    import pandas as pd
        
    if lasFileName.endswith('.las'):
        las = laspy.read(lasFileName)
        point_format = las.point_format
        lidar_points = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
        lidar_df = pd.DataFrame(lidar_points)
        lidar_df[0] = lidar_df[0]/100
        lidar_df[1] = lidar_df[1]/100
        lidar_df[2] = lidar_df[2]/100
        lidar_df.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns']
    
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

def footprintPointsFromGeoJSON(filepath):
    import json
    
    points = []
    
    with open(filepath) as f:
        features = json.load(f)["features"]

    for feature in features:
        height = feature["properties"]["heightroof"] ################## verify this is the correct attribute name
        for polygonPart in feature["geometry"]["coordinates"]:
            for polygonSubPart in polygonPart:
                for coordinates in polygonSubPart:
                    point = [coordinates[0],coordinates[1],height]
                    points.append(point)
                    
    return points, height

#

def convertCoords(x,y):
    from pyproj import Transformer
    transformer = Transformer.from_crs("epsg:2263", "epsg:4326")
    lat, lon = transformer.transform(x, y)
    return lat, lon

#

def convertLatLon(lat,lon):
    from pyproj import Transformer
    #translate from geojson CRS (NAD 1983) to .las CRS (UTM Zone 18N (meters))
    transformer = Transformer.from_crs( "epsg:4326", "epsg:2263" ) 
    x, y = transformer.transform(lat, lon)
    return x, y

#

def projectToGround(point,az,amp):
    
    import math
    
    sinAz = math.sin( math.radians( az ) )
    cosAz = math.cos( math.radians( az ) )
    tanAz = math.tan( math.radians( az ) )
    sinAmp = math.sin( math.radians(amp-90) )
    cosAmp = math.cos( math.radians(amp-90) )
    tanAmp = math.tan( math.radians(-amp) )
    
    pointGroundX = point[0] + ((point[2])/(tanAmp*sinAz))
    
    pointGroundY = point[1] + ((point[2])/(tanAmp*cosAz))
    
    pointGroundZ =  point[2] * 0
    
    return pointGroundX,pointGroundY,pointGroundZ

#

def projectToGroundX(point,az,amp):
    
    import math
    
    sinAz = math.sin( math.radians( az ) )
    cosAz = math.cos( math.radians( az ) )
    tanAz = math.tan( math.radians( az ) )
    sinAmp = math.sin( math.radians(amp-90) )
    cosAmp = math.cos( math.radians(amp-90) )
    tanAmp = math.tan( math.radians(-amp) )
    
    pointGroundX = point[0] + ((point[2])/(tanAmp*sinAz))
        
    return pointGroundX

#

def projectToGroundY(point,az,amp):
    
    import math
    
    sinAz = math.sin( math.radians( az ) )
    cosAz = math.cos( math.radians( az ) )
    tanAz = math.tan( math.radians( az ) )
    sinAmp = math.sin( math.radians(amp-90) )
    cosAmp = math.cos( math.radians(amp-90) )
    tanAmp = math.tan( math.radians(-amp) )
    
    pointGroundY = point[1] + ((point[2])/(tanAmp*cosAz))
    
    return pointGroundY

#

def pointsForHull(points,az,amp):
    groundPointList = []

    for point in points:
        #print(point)
        point[0],point[1] = convertLatLon(point[1],point[0])
        #print(point)
        groundPointList.append([point[0],point[1]])
        groundPoint = projectToGround(point,az,amp)
        #print(groundPoint)
        groundPointList.append([groundPoint[0],groundPoint[1]])
        
    return groundPointList

#

def convexHull2D(points):
    
    import numpy as np
    from scipy.spatial import ConvexHull, convex_hull_plot_2d
    import matplotlib.pyplot as plt
    
    points = np.array(points)
    
    hull = ConvexHull(points)
    
    plt.plot(points[:,0], points[:,1], 'o')
    
    for simplex in hull.simplices:
        plt.plot(points[simplex, 0], points[simplex, 1], 'k-')
        
    plt.plot(points[hull.vertices,0], points[hull.vertices,1], 'r--', lw=2)
    plt.plot(points[hull.vertices[0],0], points[hull.vertices[0],1], 'ro')
    
    plt.show()

    return hull

#

def inHull(points, hull, fieldName='inside'):
    
    import numpy as np
    import matplotlib.path as mpltPath
    from scipy.spatial import Delaunay
    
    vertexList = (hull.vertices).tolist()
    polygonPoints = []
    for index in vertexList:
        polygonPoints.append(hull.points[index])
    
    path = mpltPath.Path(polygonPoints)
    
    pointsIn = points[['groundX','groundY']]
    #pointsIn = pointsIn.to_numpy()
    points[fieldName] = path.contains_points(pointsIn)
    
    return points
        


#

############################################################################################################################################################################

lasdf = processLas('las/995237.las')

groundElevation = lasdf[lasdf['class']==2]['Z'].mean()

lasdf = lasDFcanopy(lasdf)

xMin = 996609.66
xMax = 996881.09
yMin = 238841.95
yMax = 239024.40

#az here is geometric degrees (counterclockwise, north = 90) not compass heading degrees (clockwise, north = 0)
az = 250.0
amp = 70.0

lasdf = lasDFclip(lasdf,xMin,xMax,yMin,yMax)

lasdf['Z'] = lasdf['Z'] - groundElevation

southBuildingPoints, southBuildingHeight = footprintPointsFromGeoJSON('buildings/singleBuildingSouth.geojson')
southBuildingPointsGround = pointsForHull(southBuildingPoints,az,amp)
southBuildingHull = convexHull2D(southBuildingPointsGround)

northBuildingPoints, northBuildingHeight = footprintPointsFromGeoJSON('buildings/singleBuildingNorth.geojson')
northBuildingPointsGround = pointsForHull(northBuildingPoints,az,amp)
northBuildingHull = convexHull2D(northBuildingPointsGround)

lasdf['groundX'] = lasdf.apply(lambda x: projectToGroundX([x['X'],x['Y'],x['Z']],az,amp) , axis=1)
lasdf['groundY'] = lasdf.apply(lambda x: projectToGroundY([x['X'],x['Y'],x['Z']],az,amp) , axis=1)

lasdf = inHull(lasdf,southBuildingHull,'insideSouth')
lasdf = inHull(lasdf,northBuildingHull,'insideNorth')

inPointsSouthTrue = lasdf[lasdf['insideSouth'] == True]
inPointsSouthFalse = lasdf[lasdf['insideSouth'] == False]

inPointsNorthTrue = inPointsSouthFalse[inPointsSouthFalse['insideNorth'] == True]
inPointsNorthFalse = inPointsSouthFalse[inPointsSouthFalse['insideNorth'] == False]

print(inPointsNorthTrue)
print(inPointsNorthFalse)

import matplotlib.pyplot as plt
plt.scatter(inPointsSouthTrue['groundX'],inPointsSouthTrue['groundY'],marker="+",s=1,c='red')
plt.scatter(inPointsNorthTrue['groundX'],inPointsNorthTrue['groundY'],marker="+",s=1,c='blue')
plt.scatter(inPointsNorthFalse['groundX'],inPointsNorthFalse['groundY'],marker="+",s=1,c='green')
plt.show()










