#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 23 10:44:58 2021
@author: Joe
"""

import pandas as pd
from pathlib import Path
import json

# read tree csv into dataframe
tree_csv = 'data/csv/2015StreetTreesCensus_TREES.csv'
trees_df_master = pd.read_csv(tree_csv)

#unique values for zip codes and species to build directories and csvs
zipcode_list = pd.unique(trees_df_master['zipcode'])

for zipcode in zipcode_list:
    trees_df_zipcode = trees_df_master[trees_df_master['zipcode'] == zipcode]
    spc_common_list = pd.unique(trees_df_zipcode['spc_common'])
    for spc_common in spc_common_list:
        filepath = "data/folio/{}/{}".format(zipcode,spc_common)
        Path(filepath).mkdir(parents=True, exist_ok=True)
        trees_df_zipcode_species = trees_df_zipcode[trees_df_zipcode['spc_common'] == spc_common]
        #trees_df_zipcode_species.to_csv('{}/trees.csv'.format(filepath), float_format='%.4f')
        result = trees_df_zipcode_species.to_json(orient="index")
        parsed = json.loads(result)
        with open('{}/trees.json'.format(filepath), 'w', encoding='utf-8') as f:
            json.dump(parsed, f, ensure_ascii=False)
