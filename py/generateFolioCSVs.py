#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 23 10:44:58 2021
@author: Joe
"""

# this script creates subsets of the street tree census CSV divided into zipcodes, and in turn species
# the resulting JSON's are used to inform the tree "portrait" pages
# the JSON must be present for folio pages to retrieve the attributes of each tree

import pandas as pd
from pathlib import Path
import json

# read tree csv into dataframe
tree_csv = 'data/csv/2015StreetTreesCensus_TREES.csv'
trees_df_master = pd.read_csv(tree_csv)

# turn unique values for zip codes into an iterable list without duplicates to build directories and csvs
zipcode_list = pd.unique(trees_df_master['zipcode'])

# iterate over unique zipcodes
for zipcode in zipcode_list:
    # filter the master dataframe down to the current zipcode
    trees_df_zipcode = trees_df_master[trees_df_master['zipcode'] == zipcode]
    # turn the unique tree species present in the zipcode into an iterable list
    spc_common_list = pd.unique(trees_df_zipcode['spc_common'])
    # iterate over unique species 
    for spc_common in spc_common_list:
        filepath = "data/folio/{}/{}".format(zipcode,spc_common)
        Path(filepath).mkdir(parents=True, exist_ok=True)
        # filter the dataframe for the current zipcode down to a single species
        trees_df_zipcode_species = trees_df_zipcode[trees_df_zipcode['spc_common'] == spc_common]
        #trees_df_zipcode_species.to_csv('{}/trees.csv'.format(filepath), float_format='%.4f')
        #convert the pandas dataframe to json and save in the correct directory alongside the individual tree point cloud JSON's
        result = trees_df_zipcode_species.to_json(orient="index")
        parsed = json.loads(result)
        with open('{}/trees.json'.format(filepath), 'w', encoding='utf-8') as f:
            json.dump(parsed, f, ensure_ascii=False)
