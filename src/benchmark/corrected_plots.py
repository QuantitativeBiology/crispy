#!/usr/bin/env python
# Copyright (C) 2017 Emanuel Goncalves

import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime as dt
from scipy.stats.stats import rankdata
from sklearn.metrics.ranking import auc
from matplotlib.gridspec import GridSpec


# - Imports
# Essential genes
essential = list(pd.read_csv('data/resources/curated_BAGEL_essential.csv', sep='\t')['gene'])

# Chromosome cytobands
cytobands = pd.read_csv('data/resources/cytoBand.txt', sep='\t')
print('[%s] Misc files imported' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))

# CRISPR
crispr = pd.read_csv('data/gdsc/crispr/deseq_gene_fold_changes.csv', index_col=0)

# CIRSPR segments
crispr_seg = pd.read_csv('data/gdsc/crispr/segments_cbs_deseq2.csv')
print('[%s] CRISPR data imported' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))

# Copy-number absolute counts
cnv = pd.read_csv('data/gdsc/copynumber/Gene_level_CN.txt', sep='\t', index_col=0)
cnv = cnv.loc[{i.split('_')[0] for i in crispr.index}, crispr.columns].dropna(how='all').dropna(how='all', axis=1)
cnv_abs = cnv.applymap(lambda v: int(v.split(',')[0]))
cnv_loh = cnv.applymap(lambda v: v.split(',')[2])

# Copy-number segments
cnv_seg = pd.read_csv('data/gdsc/copynumber/Summary_segmentation_data_994_lines_picnic.txt', sep='\t')
cnv_seg['chr'] = cnv_seg['chr'].replace(23, 'X').replace(24, 'Y').astype(str)
print('[%s] Copy-number data imported' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))


# -
sample_files = [os.path.join('data/crispy/', f) for f in os.listdir('data/crispy/')]

sample = 'AU565'
df = pd.concat([pd.read_csv(f, index_col=0) for f in sample_files if f.startswith('data/crispy/%s_' % sample)])


# - Evaluate
sns.set(style='ticks', context='paper', font_scale=0.75, palette='PuBu_r', rc={'axes.linewidth': .3, 'xtick.major.width': .3, 'ytick.major.width': .3, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.direction': 'in', 'ytick.direction': 'in'})
for f in ['logfc', 'logfc_norm']:
    # Build data-frame
    plot_df = df.sort_values(f).copy()

    # Rank fold-changes
    x = rankdata(plot_df[f]) / plot_df.shape[0]

    # Observed cumsum
    y = plot_df['essential'].cumsum() / plot_df['essential'].sum()

    # Plot
    plt.plot(x, y, label='%s: %.2f' % (f, auc(x, y)), lw=1.)

    # Random
    plt.plot((0, 1), (0, 1), 'k--', lw=.3, alpha=.5)

    # Misc
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    plt.title('Essential: %s' % f.replace('_', ' '))
    plt.xlabel('Ranked %s' % f)
    plt.ylabel('Cumulative sum Essential')

    plt.legend(loc=4)

plt.gcf().set_size_inches(2, 2)
plt.savefig('reports/%s_eval_plot.png' % sample, bbox_inches='tight', dpi=600)
plt.close('all')
print('[%s] AROCs done.' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))


# - Scatter plot
cmap = plt.cm.get_cmap('viridis')

sns.set(style='ticks', context='paper', font_scale=0.5, rc={'axes.linewidth': .3, 'xtick.major.width': .3, 'ytick.major.width': .3, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.direction': 'in', 'ytick.direction': 'in'})

plt.scatter(df['logfc'], df['logfc_norm'], s=3, alpha=.2, edgecolor='w', lw=0.05, c=df['cnv'], cmap=cmap)

xlim, ylim = plt.xlim(), plt.ylim()
xlim, ylim = np.min([xlim[0], ylim[0]]), np.max([xlim[1], ylim[1]])
plt.plot((xlim, ylim), (xlim, ylim), 'k--', lw=.3, alpha=.5)
plt.xlim((xlim, ylim))
plt.ylim((xlim, ylim))

plt.axhline(0, lw=.1, c='black', alpha=.5)
plt.axvline(0, lw=.1, c='black', alpha=.5)

plt.xlabel('Original FCs')
plt.ylabel('Corrected FCs')

plt.colorbar()

plt.title(sample)

plt.gcf().set_size_inches(2, 1.8)
plt.savefig('reports/%s_crispy_norm_scatter.png' % sample, bbox_inches='tight', dpi=600)
plt.close('all')
print('[%s] Scatter plot done.' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))


# -
plot_df = df.dropna(subset=['cnv', 'logfc', 'logfc_norm'])
plot_df = plot_df[plot_df['cnv'] != -1]

plot_df['logfc_ranked'] = rankdata(plot_df['logfc']) / plot_df.shape[0]
plot_df['logfc_norm_ranked'] = rankdata(plot_df['logfc_norm']) / plot_df.shape[0]

plot_df['cnv'] = plot_df['cnv'].astype(int)

sns.set(style='ticks', context='paper', font_scale=0.5, rc={'axes.linewidth': .3, 'xtick.major.width': .3, 'ytick.major.width': .3, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.direction': 'out', 'ytick.direction': 'out'})
(f, axs), pos = plt.subplots(2), 0
for i in ['logfc_ranked', 'logfc_norm_ranked']:
    sns.boxplot('cnv', i, data=plot_df, linewidth=.3, notch=True, fliersize=1, orient='v', palette='viridis', ax=axs[pos])
    axs[pos].set_xlabel('')
    axs[pos].set_ylabel(i)
    pos += 1

plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)

plt.suptitle(sample)
plt.xlabel('Copy-number (absolute)')

plt.gcf().set_size_inches(2, 2)
plt.savefig('reports/%s_crispy_norm_boxplots.png' % sample, bbox_inches='tight', dpi=600)
plt.close('all')


# - Chromossome plot
sns.set(style='ticks', context='paper', font_scale=0.75, rc={'axes.linewidth': .3, 'xtick.major.width': .3, 'ytick.major.width': .3, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.direction': 'in', 'ytick.direction': 'in'})
gs, pos = GridSpec(len(set(df['CHRM'])), 1, hspace=.4, wspace=.1), 0

for sample_chr in set(df['CHRM']):
    # Define plot data-frame
    ax = plt.subplot(gs[pos])
    plot_df = df[df['CHRM'] == sample_chr]

    # Cytobads
    for i in cytobands[cytobands['chr'] == 'chr%s' % sample_chr].index:
        s, e, t = cytobands.loc[i, ['start', 'end', 'band']].values

        if t == 'acen':
            ax.axvline(s, lw=.2, ls='-', color='#b1b1b1', alpha=.3)
            ax.axvline(e, lw=.2, ls='-', color='#b1b1b1', alpha=.3)

        elif not i % 2:
            ax.axvspan(s, e, alpha=0.2, facecolor='#b1b1b1')

    # Plot guides
    ax.scatter(plot_df['STARTpos'], plot_df['logfc'], s=2, marker='.', lw=0, c='#b1b1b1', alpha=.5)

    # Plot CRISPR segments
    for s, e, fc in crispr_seg.loc[(crispr_seg['sample'] == sample) & (crispr_seg['chrom'] == str(sample_chr)), ['loc.start', 'loc.end', 'seg.mean']].values:
        ax.plot([s, e], [fc, fc], lw=.3, c='#ff511d', alpha=.9)

    # Plot CNV segments
    for s, e, c in cnv_seg.loc[(cnv_seg['cellLine'] == sample) & (cnv_seg['chr'] == str(sample_chr)), ['startpos', 'endpos', 'totalCN']].values:
        ax.plot([s, e], [c, c], lw=.3, c='#3498db', alpha=.9)

    # Plot sgRNAs mean
    ax.scatter(plot_df['STARTpos'], plot_df['logfc_mean'], s=4, marker='.', lw=0, c='#2ecc71', alpha=.9)

    # Misc
    ax.axhline(0, lw=.3, ls='-', color='black')

    # Labels and dim
    ax.set_ylabel('chr%s' % sample_chr)
    ax.set_xlim(0, plot_df['STARTpos'].max())

    if pos == 0:
        ax.set_title(sample)

    pos += 1

plt.gcf().set_size_inches(3, 20)
plt.savefig('reports/%s_chromosome_plot.png' % sample, bbox_inches='tight', dpi=600)
plt.close('all')
print('[%s] Chromossome plot done.' % dt.now().strftime('%Y-%m-%d %H:%M:%S'))
