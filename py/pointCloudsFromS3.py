#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 28 18:03:40 2022

@author: joe
"""

import numpy as np
import pandas as pd
import boto3
from botocore import UNSIGNED
from botocore.client import Config
import json
from pyproj import Transformer
import laspy #ensure laz handler installed: pip install "laspy[lazrs,laszip]"
import matplotlib.pyplot as plt
import os

#

def convertLatLon(lat,lon):
    #uses the coodinate system that the Entwine Point Tiles are provided in
    transformer = Transformer.from_crs( "epsg:4326", "epsg:3857" ) 
    x, y = transformer.transform(lat, lon)
    return x, y

#

#can be copied from Google Maps...
lat,lon = 40.70104756900311, -74.01311202477183
x,y = convertLatLon(lat,lon)

s3 = boto3.resource('s3', config=Config(signature_version=UNSIGNED))
bucket = s3.Bucket('usgs-lidar-public')

prefix = 'NY_NewYorkCity/'

for obj in bucket.objects.filter(Prefix= prefix + 'ept.json'):
    key = obj.key
    body = obj.get()['Body']
    eptJson = json.load(body)
    print(eptJson)
    span = eptJson['span']
    xmin = eptJson['boundsConforming'][0]
    ymin = eptJson['boundsConforming'][1]
    zmin = eptJson['boundsConforming'][2]
    xmax = eptJson['boundsConforming'][3]
    ymax = eptJson['boundsConforming'][4]
    zmax = eptJson['boundsConforming'][5]
    
locatorx = ( x - xmin ) / ( xmax - xmin ) 
locatory = ( y - ymin ) / ( ymax - ymin )
print(locatorx," ",locatory)

try:
    os.mkdir('laz/')
except:
    pass

# download highest level laz for entire extent
lazfile = bucket.download_file(prefix + 'ept-data/0-0-0-0.laz','laz/0-0-0-0.laz')
with laspy.open('laz/0-0-0-0.laz') as lz:
    print(lz.header.scales)
    las = lz.read()
    lidarPoints = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
    lidar_df = pd.DataFrame(lidarPoints)
    lidar_df.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns']
    lidar_df['X'] = lidar_df['X'] * lz.header.scales[0] + lz.header.offsets[0]
    lidar_df['Y'] = lidar_df['Y'] * lz.header.scales[1] + lz.header.offsets[1]
    lidar_df['Z'] = lidar_df['Z'] * lz.header.scales[2] + lz.header.offsets[2]

print(lidar_df)
        
for depth in range(1,11):
    binx = int( (locatorx * 2 ** ( depth ) ) // 1 ) 
    biny = int( (locatory * 2 ** ( depth ) ) // 1 ) 

    print(binx,", ",biny,", ", 2 ** ( depth ))

    lazfile = prefix + 'ept-data/{}-{}-{}-'.format(depth,binx,biny)
    for obj in bucket.objects.filter(Prefix = lazfile ):
        key = obj.key
        print(key)
        lazfilename = key.split('/')[2]
        # download subsequent laz files and concat 
        if os.path.exists('laz/'+lazfilename) == False:
            lazfile = bucket.download_file(prefix + 'ept-data/'+lazfilename,'laz/'+lazfilename)
        else: 
            pass
        with laspy.open('laz/'+lazfilename) as lz:
            las = lz.read()
            lidarPoints = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
            lidar_df2 = pd.DataFrame(lidarPoints)
            lidar_df2.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns']
            lidar_df2['X'] = lidar_df2['X'] * lz.header.scales[0] + lz.header.offsets[0]
            lidar_df2['Y'] = lidar_df2['Y'] * lz.header.scales[1] + lz.header.offsets[1]
            lidar_df2['Z'] = lidar_df2['Z'] * lz.header.scales[2] + lz.header.offsets[2]
        lidar_df = pd.concat([lidar_df,lidar_df2])
            
print(lidar_df)

lidar_df = lidar_df[lidar_df['Z'] > 0]
lidar_df = lidar_df[lidar_df['Z'] < 100]

fig = plt.figure(figsize=(12,12), dpi=300, constrained_layout=True)
ax1 = fig.add_subplot()
ax1.scatter(lidar_df['X'],lidar_df['Y'],marker="+",s=0.01,c=lidar_df['Z'],cmap='bone')

boxSize = 100

lidar_df = lidar_df[lidar_df['X'] <= x + boxSize/2 ]
lidar_df = lidar_df[lidar_df['X'] >= x - boxSize/2 ]
lidar_df = lidar_df[lidar_df['Y'] <= y + boxSize/2 ]
lidar_df = lidar_df[lidar_df['Y'] >= y - boxSize/2 ]

print(lidar_df)


