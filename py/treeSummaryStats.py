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

def countDataFrame(treeJSONpath):
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

###############################################################################

# dates = ['2022_06_21','2022_08_07','2022_09_22','2022_11_07','2022_12_21']
# times = ['0800','0900','1000','1100','1200','1300','1400','1500','1600']
# conditions = ['inShade','shadingFacade','shadingGround']

# treedf['lidarTile'] = treedf.apply(lambda x: tileids[x['tree_id']] , axis=1)

# print(treedf)

# for date in dates:
#     for time in times:
#         for condition in conditions:           
#             treedf['{}_{}_{}'.format(date,time,condition)] = treedf.apply(lambda x: countDataFrame('shadeShadingShadedTrees/{}_{}_{}_tile{}_{}.json'.format( x['tree_id'], date, time, x['lidarTile'], condition )) , axis=1)

# for date in dates:
#     for time in times:
#         for condition in conditions:     
#             treedf['{}_{}_{}_proportion'.format(date,time,condition)] = treedf['{}_{}_{}'.format(date,time,condition)] / ( treedf['{}_{}_{}'.format(date,time,'inShade')] + 
#                                                                                                                           treedf['{}_{}_{}'.format(date,time,'shadingFacade')] + 
#                                                                                                                           treedf['{}_{}_{}'.format(date,time,'shadingGround')] )
            
# treedf.to_csv('treeShadeSummaryStats.csv')

###############################################################################

summaryDictSchema = {
    'treeid':[],
    'lidarTile':[],
    'year':[],
    'month':[],
    'day':[],
    'hour':[],
    'inShadeCount':[],
    'shadingGroundCount':[],
    'shadingBuildingCount':[],
    'totalPointsCount':[],
    'inShadeProportion':[],
    'shadingGroundProportion':[],
    'shadingBuildingProportion':[]
    }

summaryDF = pd.DataFrame.from_dict(summaryDictSchema)

for filename in os.listdir('shadeShadingShadedTrees/'):
    if filename.endswith('_shadingFacade.json'):
        newLineSummaryDict = summaryDictSchema
        
        treeid = filename.split('_')[0]
        year   = filename.split('_')[1]
        month  = filename.split('_')[2]
        day    = filename.split('_')[3]
        hour   = filename.split('_')[4]
        tile   = filename.split('_')[5].strip('tile')
        
        inshadefilename = 'shadeShadingShadedTrees/{}_{}_{}_{}_{}_tile{}_inShade.json'.format(treeid,year,month,day,hour,tile)
        shadinggroundfilename = 'shadeShadingShadedTrees/{}_{}_{}_{}_{}_tile{}_shadingGround.json'.format(treeid,year,month,day,hour,tile)
        shadingbuildingfilename = 'shadeShadingShadedTrees/{}_{}_{}_{}_{}_tile{}_shadingFacade.json'.format(treeid,year,month,day,hour,tile)
        
        inShadeCount = countDataFrame(inshadefilename)
        shadingGroundCount = countDataFrame(shadinggroundfilename)
        shadingBuildingCount = countDataFrame(shadingbuildingfilename)
        
        totalPointsCount = inShadeCount + shadingGroundCount + shadingBuildingCount
        
        if totalPointsCount > 0:
            inShadeProportion = inShadeCount / totalPointsCount
            shadingGroundProportion = shadingGroundCount / totalPointsCount
            shadingBuildingProportion = shadingBuildingCount / totalPointsCount
        else:
            inShadeProportion = 0
            shadingGroundProportion = 0
            shadingBuildingProportion = 0
        
        
        
        newLineSummaryDict = {
            'treeid':[treeid],
            'lidarTile':[tile],
            'year':[year],
            'month':[month],
            'day':[day],
            'hour':[hour],
            'inShadeCount':[inShadeCount],
            'shadingGroundCount':[shadingGroundCount],
            'shadingBuildingCount':[shadingBuildingCount],
            'totalPointsCount':[totalPointsCount],
            'inShadeProportion':[inShadeProportion],
            'shadingGroundProportion':[shadingGroundProportion],
            'shadingBuildingProportion':[shadingBuildingProportion]
            }
        
        
        newLineDF = pd.DataFrame.from_dict(newLineSummaryDict)
        summaryDF = pd.concat([summaryDF,newLineDF])
        summaryDF = summaryDF[[
            'treeid',
            'lidarTile',
            'year',
            'month',
            'day',
            'hour',
            'inShadeCount',
            'shadingGroundCount',
            'shadingBuildingCount',
            'totalPointsCount',
            'inShadeProportion',
            'shadingGroundProportion',
            'shadingBuildingProportion'
            ]]
        
        summaryDF.to_csv('treeShadeSummaryStatsV2.csv')
        
