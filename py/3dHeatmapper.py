#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 30 15:06:24 2022

@author: joe
"""

import numpy as np
import pandas as pd
from pointCloudsFromS3 import convertLatLon,getLazFile,stackTiles
import matplotlib.pyplot as plt

#

def buildGrid(boxSize,increment):
    bins = []
    for i in range(-boxSize,boxSize,increment):
        for j in range(-boxSize,boxSize,increment):
            for k in range(0,boxSize,increment):
                bins.append([i,j,k,0])
    countdf = pd.DataFrame(bins,columns = ['X','Y','Z','C'])
    countdf['X'] = countdf['X']
    countdf['Y'] = countdf['Y']
    countdf['Z'] = countdf['Z']
    return countdf

def recenterPointCloud(pointdf):
    midx = ( pointdf['X'].max() + pointdf['X'].min() ) / 2
    midy = ( pointdf['Y'].max() + pointdf['Y'].min() ) / 2
    ground = (pointdf[pointdf['class'] == 2 ])['Z'].mean()
    pointdf['X'] = pointdf['X'] - midx
    pointdf['Y'] = pointdf['Y'] - midy
    pointdf['Z'] = pointdf['Z'] - ground
    return pointdf

def countPointsIn3dBin(pointdf,minx,miny,minz,inc):
    maxx,maxy,maxz = minx+inc,miny+inc,minz+inc
    pointdf = pointdf[pointdf['X'] >= minx]
    pointdf = pointdf[pointdf['Y'] >= miny]
    pointdf = pointdf[pointdf['Z'] >= minz]
    pointdf = pointdf[pointdf['X'] < maxx]
    pointdf = pointdf[pointdf['Y'] < maxy]
    pointdf = pointdf[pointdf['Z'] < maxz]
    return pointdf.size
    
#

# build 3d grid for heatmap
boxSize = 10
increment = 1


#bring in point cloud
lat, lon =  40.68449261, -73.98669463 #  42.44388282145252, -76.48573793521436 #
lidar_df = stackTiles(lat,lon,boxSize*2)
print(lidar_df)
lidar_df = recenterPointCloud(lidar_df)
print(lidar_df)

lidar_df = lidar_df.round(decimals=0)

lidar_df = lidar_df.groupby(by=['X','Y','Z'],as_index=False).size()

print(lidar_df)


#

# fig = plt.figure(figsize=(12,12), dpi=300, constrained_layout=True)
# ax1 = fig.add_subplot(111, aspect='equal')
# ax1.scatter(lidar_df['X'],lidar_df['Y'],marker="+",s=50/boxSize,c=lidar_df['Z'],cmap='bone')
# trees = lidar_df[lidar_df['number_of_returns'] - lidar_df['return_number'] > 0 ]
# ax1.scatter(trees['X'],trees['Y'],marker="+",s=0.01,c=trees['Z'],cmap='summer')

#

import matplotlib.path as mpltPath
import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D

images = []

for i in range(0,360):
    
    #plt.ioff()
    plt.clf()
    
    fig = plt.figure(figsize=(3,3), dpi=600, constrained_layout=True)
    
    ax1 = fig.add_subplot(1, 1, 1, projection='3d') ############
    
    ax1.scatter3D(lidar_df['X'], lidar_df['Y'], lidar_df['Z'], zdir='z', c=-lidar_df['size'], cmap='viridis', s=lidar_df['size'], marker='+', depthshade=True)
    
    ax1.view_init(10, i)
    
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.set_zticks([])
    ax1.grid(False)
    ax1.set_axis_off()
    
    ax1.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax1.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax1.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    
    ax1.set_xlim3d(-boxSize, boxSize)
    ax1.set_ylim3d(-boxSize, boxSize)
    ax1.set_zlim3d(0, boxSize*2)
    
    fig.subplots_adjust(bottom=-0.1, top=1.1, left=-0.1, right=1.1, wspace=-0.1, hspace=-0.1)
    
    if i < 10:
        figure = 'single_image/00{}_plot.png'.format(i)
        fig.savefig(figure)
    elif i >= 10 and i < 100:
        figure = 'single_image/0{}_plot.png'.format(i)
        fig.savefig(figure)
    else:
        figure = 'single_image/{}_plot.png'.format(i)
        fig.savefig(figure)
        
    images.append(figure)
    
    #plt.clf()
    plt.close(fig)
    
    
    #plt.show()
    
import cv2
import os
import ffmpeg

image_folder = 'single_image'
video_name = 'treeRotate.mp4'

fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v') 

#images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
frame = cv2.imread(os.path.join(images[0]))
height, width, layers = frame.shape

video = cv2.VideoWriter(video_name, fourcc, 12, (width,height))

for image in images[:]:
    video.write(cv2.imread(os.path.join(image)))

cv2.destroyAllWindows()
video.release()




