#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  1 16:45:57 2022

@author: joe
"""

import json
import pandas as pd
import numpy as np
import math
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from pysolar.solar import *
import datetime
import matplotlib.pyplot as plt

###

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
        return point[0],point[1],1.0
    
def pointsForHull(points,az,amp):
    groundPointList = []
    for point in points:
        #point[0],point[1] = convertLatLon(point[1],point[0])
        groundPoint = projectToGround(point,az,amp)
        groundPointList.append([groundPoint[0],groundPoint[1]])  
    return groundPointList

def convexHull2D(points):
    points = np.array(points)
    hull = ConvexHull(points)
    return hull

###

jsonfilename = '25192_2015_MR_for_ConvexHullMask_Full.json'
with open(jsonfilename) as f:
    treeJson = json.load(f)
clusters = treeJson['MR_TreeClusterDict']
print('There are {} tree clusters in the JSON file'.format(len(clusters)))
print('')

jsonfilename2 = '25192_2015_ConvexHullMasked_Only_SRTrue_LidarSRWorkflow.json'
with open(jsonfilename2) as f:
    treeJson2 = json.load(f)
clusters2 = treeJson2['MR_TreeClusterDict']

i = 0
shadowAreaList = []
radBlockedList = []
radList = []

for cluster in clusters:
    #print(cluster)
    clusterID = cluster['ClusterID']
    clusterPoints = cluster['ConvexHullDict']['ClusterPoints']
    
    #find the matching cluster from the single return file
    for cluster2 in clusters2:
        clusterID2 = cluster2['SRpointsInfo']['SRpointsTreeCluster']
        if clusterID == clusterID2:
            clusterPoints2 = cluster2['SRpointsInfo']['SpecificClusterSRpoints']
            clusterPoints3 = clusterPoints + clusterPoints2
            with open('treeClusters/{}.json'.format(clusterID), 'w', encoding='utf-8') as f:
                json.dump(clusterPoints3, f, ensure_ascii=False)
        else:
            continue
    
    

#     latitude = cluster['PredictedTreeLocation']['Latitude']
#     longitude = cluster['PredictedTreeLocation']['Longitude']
    
#     year = 2022
#     month = 12
#     day = 21

#     for hour in range(9,16):
#         for minute in range(0,60,1):
    
#             date = datetime.datetime(year, month, day, hour+4, minute, 0, 0, tzinfo=datetime.timezone.utc)
#             az = get_azimuth(latitude, longitude, date)
#             amp = get_altitude(latitude, longitude, date)
#             rad = radiation.get_radiation_direct(date, amp)
#             radList.append(rad)
#             #print('Solar details: azimuth {}, amplitude {}, clear sky radiation {}'.format(az,amp,rad))
        
#             groundPoints = pointsForHull(clusterPoints,az,amp)
#             #print(groundPoints)
#             hull = convexHull2D(groundPoints)
#             shadowAreaList.append(hull.volume)
#             #print('Shadow area of tree cluster {} at {}:{} on {}-{}-{}: {}'.format(i,hour,minute,year,month,day,hull.volume))
#             radBlocked = int(hull.volume * rad)
#             radBlockedList.append(radBlocked)
#             #print('This tree provided shade from {} watts of solar energy at this time.'.format(radBlocked))
#             #print('')
        
#     i += 1
    
# #    

# fig, ax1 = plt.subplots()

# color = 'tab:red'
# ax1.set_xlabel('time (5 min)')
# ax1.set_ylabel('clear sky radiation (watts per sq meter)', color=color)
# #ax1.plot(radList, color=color)
# #ax1.tick_params(axis='y', labelcolor=color)

# ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

# color = 'tab:blue'
# ax2.set_ylabel('shadow area', color=color)  # we already handled the x-label with ax1
# ax2.plot(shadowAreaList, color=color)
# ax2.tick_params(axis='y', labelcolor=color)

# fig.tight_layout()  # otherwise the right y-label is slightly clipped
# plt.show()


