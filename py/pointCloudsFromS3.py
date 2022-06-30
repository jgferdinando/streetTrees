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

def convertLatLon(lat,lon,epsgNumber):
    #uses the coodinate system that the Entwine Point Tiles are provided in
    transformer = Transformer.from_crs( "epsg:4326", "epsg:{}".format(epsgNumber) ) 
    x, y = transformer.transform(lat, lon)
    return x, y

def getLazFile(lazfilename):
    with laspy.open(lazfilename) as lz:
        las = lz.read()
        lidarPoints = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
        lidarDF = pd.DataFrame(lidarPoints)
        lidarDF.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns']
        lidarDF['X'] = lidarDF['X'] * lz.header.scales[0] + lz.header.offsets[0]
        lidarDF['Y'] = lidarDF['Y'] * lz.header.scales[1] + lz.header.offsets[1]
        lidarDF['Z'] = lidarDF['Z'] * lz.header.scales[2] + lz.header.offsets[2]
    return lidarDF

def stackTiles(lat,lon):

    s3 = boto3.resource('s3', config=Config(signature_version=UNSIGNED))
    bucket = s3.Bucket('usgs-lidar-public')
    
    prefix = 'NY_NewYorkCity/'
    
    for obj in bucket.objects.filter(Prefix= prefix + 'ept.json'):
        key = obj.key
        body = obj.get()['Body']
        eptJson = json.load(body)
        epsgNumber = eptJson['srs']['horizontal']
        span = eptJson['span']
        [xmin,ymin,zmin,xmax,ymax,zmax] = eptJson['boundsConforming']
      
    x,y = convertLatLon(lat,lon,epsgNumber)   
    locatorx = ( x - xmin ) / ( xmax - xmin ) 
    locatory = ( y - ymin ) / ( ymax - ymin )
    
    try:
        os.mkdir('laz/')
    except:
        pass
    
    # download highest level laz for entire extent
    lazfile = bucket.download_file(prefix + 'ept-data/0-0-0-0.laz','laz/0-0-0-0.laz')
    lidar_df = getLazFile('laz/0-0-0-0.laz')
            
    for depth in range(1,11):
        binx = int( (locatorx * 2 ** ( depth ) ) // 1 ) 
        biny = int( (locatory * 2 ** ( depth ) ) // 1 ) 
    
        lazfile = prefix + 'ept-data/{}-{}-{}-'.format(depth,binx,biny)
        for obj in bucket.objects.filter(Prefix = lazfile ):
            key = obj.key
            lazfilename = key.split('/')[2]
            # download subsequent laz files and concat 
            if os.path.exists('laz/'+lazfilename) == False:
                lazfile = bucket.download_file(prefix + 'ept-data/'+lazfilename,'laz/'+lazfilename)
            else: 
                pass
            lidar_df2 = getLazFile('laz/'+lazfilename)
            lidar_df = pd.concat([lidar_df,lidar_df2])
                    
    lidar_df = lidar_df[lidar_df['Z'] > 0]
    lidar_df = lidar_df[lidar_df['Z'] < 30]
    
    boxSize = 500
    
    lidar_df = lidar_df[lidar_df['X'] <= x + boxSize/2 ]
    lidar_df = lidar_df[lidar_df['X'] >= x - boxSize/2 ]
    lidar_df = lidar_df[lidar_df['Y'] <= y + boxSize/2 ]
    lidar_df = lidar_df[lidar_df['Y'] >= y - boxSize/2 ]
    
    return lidar_df

###

lidar_df = stackTiles(40.68569409821998, -73.98782434876196)

fig = plt.figure(figsize=(12,12), dpi=300, constrained_layout=True)
ax1 = fig.add_subplot(111, aspect='equal')
ax1.scatter(lidar_df['X'],lidar_df['Y'],marker="+",s=0.01,c=lidar_df['Z'],cmap='bone')
trees = lidar_df[lidar_df['number_of_returns'] - lidar_df['return_number'] > 0 ]
ax1.scatter(trees['X'],trees['Y'],marker="+",s=0.01,c=trees['Z'],cmap='summer')


