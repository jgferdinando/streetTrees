#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 16 17:37:42 2022

@author: joe
"""

#import libraries
import pandas as pd
import os
import json
import itertools

def countDataFrame(treeFilePath):
    treeJSONpath = 'shadeShadingShadedTrees/{}'.format(treeFilePath)
    if os.path.exists(treeJSONpath):
        with open(treeJSONpath) as f:
            treePoints = json.load(f)
        return len(treePoints)
    else:
        return 0
    
    
    

        
# read tree csv into dataframe
tree_csv = 'csv/2015StreetTreesCensus_TREES.csv'
treedf = pd.read_csv(tree_csv)

treeids = []
tileids = {}

# find trees in dataset
for filename in os.listdir('shadeShadingShadedTrees/'):
    if filename.endswith('.json'):
        treeid = int(filename.split('_')[0])
        tileid = int(filename.split('_')[5].strip('tile'))
        if treeid in treeids:
            continue
        else:
            treeids.append(treeid)
            tileids.update({treeid:tileid})   

treedf = treedf[treedf['tree_id'].isin(treeids)]

dates = ['2022_06_21','2022_08_07','2022_09_22','2022_11_07','2022_12_21']
times = ['0800','0900','1000','1100','1200','1300','1400','1500','1600']
conditions = ['inShade','shadingFacade','shadingGround']

treedf['lidarTile'] = treedf.apply(lambda x: tileids[x['tree_id']] , axis=1)

print(treedf)

for date in dates:
    for time in times:
        for condition in conditions:           
            treedf['{}_{}_{}'.format(date,time,condition)] = treedf.apply(lambda x: countDataFrame('{}_{}_{}_tile{}_{}.json'.format( x['tree_id'], date, time, x['lidarTile'], condition )) , axis=1)

for date in dates:
    for time in times:
        for condition in conditions:     
            treedf['{}_{}_{}_proportion'.format(date,time,condition)] = treedf['{}_{}_{}'.format(date,time,condition)] / ( treedf['{}_{}_{}'.format(date,time,'inShade')] + 
                                                                                                                          treedf['{}_{}_{}'.format(date,time,'shadingFacade')] + 
                                                                                                                          treedf['{}_{}_{}'.format(date,time,'shadingGround')] )
            
treedf.to_csv('treeShadeSummaryStats.csv')