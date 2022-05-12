#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 12 12:23:38 2022

@author: joe
"""

import pandas as pd
import matplotlib.pyplot as plt

tiles = ['25252','32187','987180']

dates = ['2022_06_21','2022_08_07','2022_09_22','2022_11_07','2022_12_21']

times = ['0800','0900','1000','1100','1200','1300','1400','1500','1600']

for tile in tiles:
    for date in dates:
        for time in times:
            lasShadeRoad = pd.read_csv('shadeShadingShadedDataframes/{}_{}_tile{}_shadingGround.csv'.format(date,time,tile))
            lasInShade = pd.read_csv('shadeShadingShadedDataframes/{}_{}_tile{}_inShade.csv'.format(date,time,tile))
            lasShadeFacade = pd.read_csv('shadeShadingShadedDataframes/{}_{}_tile{}_shadingFacade.csv'.format(date,time,tile))

            plt.ioff()
            plt.clf()
            
            fig = plt.figure(figsize=(12,12), dpi=300, constrained_layout=True)
            
            ax1 = fig.add_subplot()
            
            #ax1.scatter(lasBuildings['X'],lasBuildings['Y'],marker="+",s=2,c=lasBuildings['Z'],cmap='binary')
            ax1.scatter(lasShadeRoad['X'],lasShadeRoad['Y'],marker="+",s=0.01,c=lasShadeRoad['Z'],cmap='summer')
            ax1.scatter(lasInShade['X'],lasInShade['Y'],marker="+",s=0.01,c=lasInShade['Z'],cmap='bone')
            ax1.scatter(lasShadeFacade['X'],lasShadeFacade['Y'],marker="+",s=0.01,c=lasShadeFacade['Z'],cmap='pink')
            
            ax1.set_axis_off()
            
            ratio = 1.0
            xMin, xMax = ax1.get_xlim()
            yMin, yMax = ax1.get_ylim()
            ax1.set_aspect( abs( ( xMax - xMin ) / ( yMin - yMax ) ) * ratio )
            
            fig.savefig('shadeShadingShadedPlots/tile_{}_{}_{}_plot.png'.format(tile,date,time))
            
            plt.clf()
            plt.close(fig)
            
