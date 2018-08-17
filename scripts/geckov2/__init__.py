#!/usr/bin/env python
# Copyright (C) 2018 Emanuel Goncalves

import numpy as np
import pandas as pd

DIR = 'data/geckov2/'

SAMPLESHEET = 'Achilles_v3.3.8.samplesheet.txt'
RAW_COUNTS = 'Achilles_v3.3.8_rawreadcounts.gct'

COPYNUMBER = 'Achilles_v3.3.8_ABSOLUTE_CN_segtab.txt'
SGRNA_MAP = 'Achilles_v3.3.8_sgRNA_mappings.txt'

PLASMID = 'pDNA_pXPR003_120K_20140624'


def get_samplesheet():
    return pd.read_csv(f'{DIR}/{SAMPLESHEET}', sep='\t', index_col=1)


def get_raw_counts():
    return pd.read_csv(f'{DIR}/{RAW_COUNTS}', index_col=0, skiprows=2, sep='\t').drop('Description', axis=1)


def get_copy_number_segments():
    columns = dict(Chromosome='chr', Start='start', End='end', CN='copy_number')

    df = pd.read_csv(f'{DIR}/{COPYNUMBER}', sep='\t').rename(columns=columns)
    df['chr'] = df['chr'].apply(lambda v: f'chr{v}')

    return df


def bin_bkdist(distance):
    if distance == -1:
        bin_distance = 'diff. chr.'

    elif distance == 0:
        bin_distance = '0'

    elif 1 < distance < 10e3:
        bin_distance = '1-10 kb'

    elif 10e3 < distance < 100e3:
        bin_distance = '10-100 kb'

    elif 100e3 < distance < 1e6:
        bin_distance = '0.1-1 Mb'

    elif 1e6 < distance < 10e6:
        bin_distance = '1-10 Mb'

    else:
        bin_distance = '>10 Mb'

    return bin_distance


def lib_off_targets():
    lib = pd.read_csv(f'{DIR}/{SGRNA_MAP}', sep='\t').dropna(subset=['Chromosome', 'Pos', 'Strand'])

    lib = lib.rename(columns={'Chromosome': '#chr', 'Pos': 'start'})

    lib['sgrna'] = lib['Guide'].apply(lambda v: v.split('_')[0])
    lib['gene'] = lib['Guide'].apply(lambda v: v.split('_')[1])
    lib['start'] = lib['start'].astype(int)
    lib['end'] = lib['start'] + lib['sgrna'].apply(len) + lib['PAM'].apply(len)
    lib['cut'] = lib['#chr'] + '_' + lib['start'].astype(str)

    sgrna_maps = lib.groupby('sgrna')['cut'].agg(lambda x: len(set(x))).sort_values().rename('ncuts').reset_index()
    sgrna_maps = sgrna_maps[sgrna_maps['ncuts'] > 1]

    sgrna_nchrs = lib.groupby('sgrna')['#chr'].agg(lambda x: len(set(x)))
    sgrna_maps = sgrna_maps.assign(nchrs=sgrna_nchrs.loc[sgrna_maps['sgrna']].values)

    sgrna_genes = lib.groupby('sgrna')['gene'].agg(lambda x: ';'.join(set(x)))
    sgrna_maps = sgrna_maps.assign(genes=sgrna_genes.loc[sgrna_maps['sgrna']].values)
    sgrna_maps = sgrna_maps.assign(ngenes=sgrna_maps['genes'].apply(lambda x: len(x.split(';'))))

    sgrna_distance = lib.groupby('sgrna')['start'].agg([np.min, np.max]).eval('amax-amin')
    sgrna_maps = sgrna_maps.assign(distance=[sgrna_distance[g] if sgrna_nchrs[g] == 1 else -1 for g in sgrna_maps['sgrna']])
    sgrna_maps = sgrna_maps.assign(distance_bin=sgrna_maps['distance'].apply(bin_bkdist).values)

    sgrna_maps = sgrna_maps.set_index('sgrna')

    return sgrna_maps


def get_crispr_library(drop_non_targeting=True, remove_off_targets=True):
    lib = pd.read_csv(f'{DIR}/{SGRNA_MAP}', sep='\t')

    lib['sgrna'] = lib['Guide'].apply(lambda v: v.split('_')[0])
    lib['gene'] = lib['Guide'].apply(lambda v: v.split('_')[1])

    if drop_non_targeting:
        lib = lib.dropna(subset=['Chromosome', 'Pos', 'Strand'])

    if remove_off_targets:
        off_targets = lib_off_targets()
        lib = lib[~lib['sgrna'].isin(off_targets.index)]

    lib = lib.rename(columns={'Chromosome': 'chr', 'Pos': 'start'})

    lib['start'] = lib['start'].astype(int)
    lib['end'] = lib['start'] + lib['sgrna'].apply(len) + lib['PAM'].apply(len)

    return lib
