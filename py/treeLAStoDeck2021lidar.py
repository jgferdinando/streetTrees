#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 28 23:36:22 2021

@author: Joe
"""

#import needed libraries
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
import matplotlib.path as mpltPath
#import matplotlib as mpl
#from mpl_toolkits.mplot3d import Axes3D
from scipy.spatial import Voronoi #, voronoi_plot_2d
import os
import laspy
from multiprocessing import Pool
from pyproj import Transformer
#from datetime import datetime
import json

#convert tree points inside the tile to voronoi polygons with tree's attributes
def voronoi_funct(input_dataframe):
  df = input_dataframe[['x_sp','y_sp']]
  point_array = df.to_numpy()
  vor = Voronoi(point_array)
  regions = []
  for region in vor.regions:
      region_points = []
      for point_index in region:
          region_points.append((vor.vertices[point_index]).tolist())
      regions.append(region_points)
  return regions

def convertCoords(x,y):
    transformer = Transformer.from_crs("epsg:2263", "epsg:4326")
    lat, lon = transformer.transform(x, y)
    return lat, lon

def clipTreeCloud(polygon):
    if len(polygon) >= 3:
        path = mpltPath.Path(polygon)
        
        lidar_df_2 = lidar_df.copy()
        trees_df_2 = trees_df.copy()
        
        lidar_points = lidar_df[[0,1]]
        lidar_points = lidar_points.to_numpy()
        lidar_df_2['inside'] = path.contains_points(lidar_points)
        lidar_df_2 = lidar_df_2.loc[lidar_df_2.inside, :]
        
        tree_stem = trees_df_2[['x_sp','y_sp']]
        tree_stem = tree_stem.to_numpy()
        trees_df_2['inside'] = path.contains_points(tree_stem)
        trees_df_2 = trees_df_2.loc[trees_df_2.inside, :].reset_index()
        
        #canopy extent radius
        tree_dbh_ft = trees_df_2.iloc[0]['tree_dbh'] / 12
        tree_dbh_m = tree_dbh_ft / 3.28
        trunk_area_sq_m = 3.1415926 * ( ( tree_dbh_m / 2 ) ** 2 )
        canopy_diameter_m = 7 + 28.2 * trunk_area_sq_m
        canopy_radius_m = canopy_diameter_m / 2
        canopy_radius = canopy_radius_m * 1.5 * 3.28 #1.5 is margin of error/buffer
        
        #distance from trunk filter
        lidar_df_2 = lidar_df_2[ ( ( (lidar_df_2[0] - trees_df_2.iloc[0]['x_sp'])**2 + (lidar_df_2[1] - trees_df_2.iloc[0]['y_sp'])**2 ) ** 0.5 ) < canopy_radius ]
        lidar_df_2 = lidar_df_2.dropna(axis=0, how='any')
        tree_id = trees_df_2.iloc[0]['tree_id']
        lidar_df_2.columns = ['X', 'Y', 'Z', 'intens', 'class', 'return_number', 'number_of_returns', 'bool']
        lidar_df_2 = lidar_df_2.drop(['bool'],axis=1)
        #normalize intensity and subtract minimum
        lidar_df_2['intens'] = (lidar_df_2['intens']-lidar_df_2['intens'].min())/(lidar_df_2['intens'].max()-lidar_df_2['intens'].min())
        
        
        
        
        #ground_df = lidar_df_2[lidar_df_2['class'].astype(int)==2]
        lidar_df_2['Z'] = (lidar_df_2['Z'] - 24)/3.28 # ground_df['Z'].mean())/3.28
        
        
        
        
        lidar_df_zeroed = lidar_df_2.copy()
        lidar_df_zeroed['X'] = lidar_df_zeroed['X'] - trees_df_2.iloc[0]['x_sp']
        lidar_df_zeroed['Y'] = lidar_df_zeroed['Y'] - trees_df_2.iloc[0]['y_sp']
        lidar_df_zeroed = lidar_df_zeroed.dropna(axis=0, how='any')
        lidar_df_zeroed.to_csv('csv_out/{}.csv'.format(tree_id), float_format='%.4f')
        
        #convert from stateplane to lat lon
        lidar_df_2['lat'] = convertCoords(lidar_df_2['X'].astype(float),lidar_df_2['Y'].astype(float))[0]
        lidar_df_2['lon'] = convertCoords(lidar_df_2['X'].astype(float),lidar_df_2['Y'].astype(float))[1]
        
        lidar_df_3 = lidar_df_2[['lat', 'lon', 'Z', 'intens', 'return_number', 'number_of_returns']].copy()
        treeArrayForDeck = lidar_df_3.to_numpy()
        treeArrayForDeck =  treeArrayForDeck.tolist()
        with open('csv_out_deck_2021/{}.json'.format(tree_id), 'w', encoding='utf-8') as f:
            json.dump(treeArrayForDeck, f, ensure_ascii=False)

    else:
        polygon = polygon


###


# read tree csv into dataframe
tree_csv = 'csv/2015StreetTreesCensus_TREES.csv'
trees_df = pd.read_csv(tree_csv)
# read las files
#lidar_df = pd.DataFrame()

for lasFileName in os.listdir('las2021/'):
    if lasFileName.endswith('.las'):
        print('starting process')
        las = laspy.read('las2021/{}'.format(lasFileName))
        point_format = las.point_format
        lidarPoints = np.array((las.X,las.Y,las.Z,las.intensity,las.classification, las.return_number, las.number_of_returns)).transpose()
        lidar_df = pd.DataFrame(lidarPoints)
        lidar_df = lidar_df[lidar_df[4].isin([3,4,5])]
        
        # find bounds of las file, select trees in lidar footprint
        lidar_df[0] = lidar_df[0]*0.00025 + 988750
        lidar_df[1] = lidar_df[1]*0.00025 + 188750
        lidar_df[2] = lidar_df[2]*0.00025
        x_min = lidar_df[0].min()
        x_max = lidar_df[0].max()
        y_min = lidar_df[1].min()
        y_max = lidar_df[1].max()
        
        print(lidar_df)
        print('min z: ', lidar_df[2].min())
        print('max z: ', lidar_df[2].max())
        
        
        trees_df2 = trees_df.copy()
        trees_df2 = trees_df2[trees_df2['x_sp']>x_min]
        trees_df2 = trees_df2[trees_df2['x_sp']<x_max]
        trees_df2 = trees_df2[trees_df2['y_sp']>y_min]
        trees_df2 = trees_df2[trees_df2['y_sp']<y_max]
        
        print(trees_df2)
        
        #generate voronoi
        vor_trees = voronoi_funct(trees_df2)
        
        #start = datetime.now()
        if __name__ == '__main__':
            with Pool() as p:
                p.map(clipTreeCloud, vor_trees)
        #end = datetime.now()
        #duration = end - start
        #duration = duration.total_seconds()
        #print('parallel process seconds: ', duration)

    else:
        continue


