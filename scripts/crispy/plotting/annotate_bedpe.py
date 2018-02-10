#!/usr/bin/env python
# Copyright (C) 2018 Emanuel Goncalves

import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from crispy import bipal_dbgd
from pybedtools import BedTool
from matplotlib.colors import rgb2hex
from crispy.utils import multilabel_roc_auc_score
from sklearn.metrics import roc_curve, auc, roc_auc_score
from crispy.ratio import BRASS_HEADERS, GFF_FILE, GFF_HEADERS
from scripts.crispy.processing.correct_cnv_bias import assemble_matrix


def import_brass_bedpe(bedpe_file, bkdist, splitreads):
    # bedpe_file = 'data/gdsc/wgs/brass_bedpe/BB65-RCC.brass.annot.bedpe'
    # Import BRASS bedpe
    bedpe_df = pd.read_csv(bedpe_file, sep='\t', names=BRASS_HEADERS, comment='#')

    # Correct sample name
    bedpe_df['sample'] = bedpe_df['sample'].apply(lambda v: v.split(',')[0])

    # SV larger than threshold
    bedpe_df = bedpe_df[bedpe_df['bkdist'] > bkdist]

    # BRASS2 annotated SV
    if splitreads:
        bedpe_df = bedpe_df.query("assembly_score != '_'")

    # Assemble bed file
    bed_df = pd.concat([
        bedpe_df['chr1'].rename('#chr').apply(lambda x: 'chr{}'.format(x)),
        bedpe_df['start1'].rename('start'),
        bedpe_df['end2'].rename('end'),
        bedpe_df['svclass'].rename('svclass')
    ], axis=1)

    return bed_df


def annotate_bed(bed_file, methods='collapse,count'):
    # Import Genes annotation bed file and specified bed file
    gff, bed = BedTool(GFF_FILE).sort(), BedTool(bed_file).sort()

    # Map GFF
    genes_sv = gff.map(bed, c=4, o='collapse,count').to_dataframe(names=GFF_HEADERS + methods.split(','))

    return genes_sv


def annotate_brass_bedpe(bedpe_dir, bkdist, splitreads):
    bed_dfs = []
    for bedpe_file in map(lambda f: '{}/{}'.format(bedpe_dir, f), filter(lambda f: f.endswith('.brass.annot.bedpe'), os.listdir(bedpe_dir))):
        print('[INFO] {}'.format(bedpe_file))

        # Import and filter bedpe
        bed_df = import_brass_bedpe(bedpe_file, bkdist, splitreads)

        if bed_df.shape[0] > 0:
            bed_file = '{}/{}.bed'.format(bedpe_dir, os.path.splitext(os.path.basename(bedpe_file))[0])
            bed_df.to_csv(bed_file, sep='\t', index=False)

            # Annotate SV with gene information
            bed_annot_df = annotate_bed(bed_file).sort_values('count', ascending=False)

            # Export
            bed_annot_file = '{}/{}.genes.gff.tab'.format(bedpe_dir, os.path.splitext(os.path.basename(bedpe_file))[0])
            bed_annot_df.to_csv(bed_annot_file, sep='\t', index=False)

            # Append df
            bed_annot_df = bed_annot_df.assign(sample=os.path.splitext(os.path.basename(bedpe_file))[0].split('.')[0])
            bed_dfs.append(bed_annot_df)

    # Assemble annotated bed dataframes
    bed_dfs = pd.concat(bed_dfs)

    # Filter genes without SVs
    bed_dfs = bed_dfs.query("collapse != '.'")

    return bed_dfs


def plot_sv_ratios_arocs(plot_df, x='ratio', order=None):
    order = ['deletion', 'inversion', 'tandem-duplication'] if order is None else order

    ax = plt.gca()

    for t, c in zip(order, map(rgb2hex, sns.light_palette(bipal_dbgd[0], len(order) + 1)[1:])):
        y_true, y_score = plot_df['collapse'].map(lambda x: t in x).astype(int), plot_df[x]

        fpr, tpr, _ = roc_curve(y_true, y_score)

        ax.plot(fpr, tpr, label='{0:} (AUC={1:.2f})'.format(t.capitalize(), auc(fpr, tpr)), lw=1., c=c)

    ax.plot((0, 1), (0, 1), 'k--', lw=.3, alpha=.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel('False positive rate')
    ax.set_ylabel('True positive rate')
    ax.set_title('Structural rearrangements relation with\ncopy-number ratio')

    ax.legend(loc=4, prop={'size': 6})

    return ax


def plot_sv_ratios_arocs_per_sample(plot_df, groupby, x='ratio', y='collapse', order=None):
    order = ['deletion', 'inversion', 'tandem-duplication'] if order is None else order
    order_color = list(map(rgb2hex, sns.light_palette(bipal_dbgd[0], len(order) + 1)[1:]))

    y_aucs = {}

    for sample in set(plot_df[groupby]):
        _plot_df = plot_df.query("{} == '{}'".format(groupby, sample)).dropna()

        y_aucs[sample] = multilabel_roc_auc_score(y, x, _plot_df, min_events=5, invert=1)

    y_aucs = pd.DataFrame(y_aucs).T.unstack().reset_index().dropna()
    y_aucs.columns = ['svclass', 'sample', 'auc']

    ax = plt.gca()

    sns.boxplot('auc', 'svclass', data=y_aucs, orient='h', order=order, palette=order_color, notch=True, linewidth=.5, fliersize=1, ax=ax)
    # sns.stripplot('auc', 'svclass', data=y_aucs, orient='h', order=order, palette=order_color, edgecolor='white', linewidth=.1, size=3, jitter=.4, ax=ax)
    plt.axvline(.5, lw=.3, c=bipal_dbgd[0])
    plt.title('Structural rearrangements relation with\ncopy-number ratio')
    plt.xlabel('Structural rearrangements ~ Copy-number ratio (AUC)')
    plt.ylabel('')

    return ax


def plot_sv_ratios_boxplots(plot_df, x='ratio', y='collapse', order=None):
    order = ['deletion', 'inversion', 'tandem-duplication'] if order is None else order

    ax = plt.gca()

    sns.boxplot(x, y, data=plot_df, orient='h', order=order, color=bipal_dbgd[0], notch=True, linewidth=.5, fliersize=1, ax=ax)
    plt.axvline(1., lw=.3, c=bipal_dbgd[0])
    plt.title('Structural rearrangements relation with\ncopy-number ratio')
    plt.xlabel('Copy-number ratio (rank)')
    plt.ylabel('')

    return ax


if __name__ == '__main__':
    bedpe_dir = 'data/gdsc/wgs/brass_bedpe'

    # Annotate BRASS bedpes
    bed_dfs = annotate_brass_bedpe(bedpe_dir, bkdist=2500, splitreads=True)
    bed_dfs.to_csv('{}/{}'.format(os.path.dirname(bedpe_dir), 'brass.genes.gff.tab'), index=False, sep='\t')

    # - Append information of copy-number ratio
    # Import copy-number
    cnv_ratios = pd.read_csv('data/crispy_copy_number_gene_ratio_wgs.csv', index_col=0)

    # Overlap
    samples = list(set(cnv_ratios).intersection(bed_dfs['sample']))
    print('Samples: {}'.format(len(samples)))

    # Append ratios
    brass = bed_dfs.assign(ratio=[cnv_ratios.loc[g, s] for s, g in bed_dfs[['sample', 'feature']].values])

    # - Exclude samples
    brass = brass[~brass['sample'].isin(['HCC1954'])]

    # - Plot: Copy-number ratio
    plot_df = brass.query('count == 1').dropna().sort_values('ratio', ascending=False)
    # plot_df = plot_df[['chr', 'collapse', 'sample', 'ratio']].drop_duplicates()
    print(plot_df)

    # AROCs
    ax = plot_sv_ratios_arocs(plot_df)

    plt.gcf().set_size_inches(3, 3)
    plt.savefig('reports/crispy/brass_sv_ratio_cumdist.png', bbox_inches='tight', dpi=600)
    plt.close('all')

    # Boxplots
    ax = plot_sv_ratios_boxplots(plot_df)

    plt.gcf().set_size_inches(3, 1)
    plt.savefig('reports/crispy/brass_sv_ratio_boxplot.png', bbox_inches='tight', dpi=600)
    plt.close('all')

    # SV enrichment per sample
    plot_sv_ratios_arocs_per_sample(plot_df, 'sample')

    plt.gcf().set_size_inches(3, 1)
    plt.savefig('reports/crispy/brass_sv_ratio_boxplot_auc.png', bbox_inches='tight', dpi=600)
    plt.close('all')

    # # - Plot: CRISPR fold-change
    # # CRISPR
    # c_gdsc_fc = pd.read_csv('data/crispr_gdsc_logfc.csv', index_col=0)
    # # c_gdsc_crispy_kmean = assemble_matrix('data/crispy/gdsc/', 'k_mean')
    #
    # # Overlap
    # samples = list(set(cnv_ratios).intersection(bed_dfs['sample']).intersection(c_gdsc_fc))
    # print('Samples: {}'.format(len(samples)))
    #
    # # Append ratios
    # brass_crispr = bed_dfs.assign(crispr=[c_gdsc_fc.loc[g, s] if s in samples and g in c_gdsc_fc.index else np.nan for s, g in bed_dfs[['sample', 'feature']].values]).dropna()
    #
    # # Plot
    # plot_df = brass_crispr.query('count == 1').dropna().sort_values('crispr', ascending=False)
    #
    # # AROCs
    # ax = plot_sv_ratios_arocs(plot_df, x='crispr')
    #
    # plt.gcf().set_size_inches(3, 3)
    # plt.savefig('reports/crispy/brass_crispr_sv_ratio_cumdist.png', bbox_inches='tight', dpi=600)
    # plt.close('all')
    #
    # # Boxplots
    # ax = plot_sv_ratios_boxplots(plot_df, x='crispr')
    #
    # plt.gcf().set_size_inches(3, 1)
    # plt.savefig('reports/crispy/brass_crispr_sv_ratio_boxplot.png', bbox_inches='tight', dpi=600)
    # plt.close('all')
    #
    # # SV enrichment per sample
    # plot_sv_ratios_arocs_per_sample(plot_df, 'sample', x='crispr')
    #
    # plt.gcf().set_size_inches(3, 1)
    # plt.savefig('reports/crispy/brass_crispr_sv_ratio_boxplot_auc.png', bbox_inches='tight', dpi=600)
    # plt.close('all')