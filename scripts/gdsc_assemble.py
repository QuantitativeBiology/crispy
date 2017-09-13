#!/usr/bin/env python
# Copyright (C) 2017 Emanuel Goncalves

import os
import pickle
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from crispy.benchmark_plot import plot_cumsum_auc, plot_chromosome, plot_cnv_rank


# - Imports
# sgRNA library
sgrna_lib = pd.read_csv('data/gdsc/crispr/KY_Library_v1.1_annotated.csv', index_col=0).dropna(subset=['STARTpos'])

# Samplesheet
ss = pd.read_csv('data/gdsc/samplesheet.csv', index_col=0)

# Essential genes
essential = pd.read_csv('data/resources/curated_BAGEL_essential.csv', sep='\t')['gene'].rename('essential genes')

# Non-expressed genes
nexp = pickle.load(open('data/gdsc/gene_expression/non_expressed_genes.pickle', 'rb'))

# Chromosome cytobands
cytobands = pd.read_csv('data/resources/cytoBand.txt', sep='\t')

# CRISPR fold-changes
fc_sgrna = pd.read_csv('data/gdsc/crispr/crispy_gdsc_fold_change_sgrna.csv', index_col=0)

# Copy-number segments
cnv_seg = pd.read_csv('data/gdsc/copynumber/Summary_segmentation_data_994_lines_picnic.txt', sep='\t')
cnv_seg['chr'] = cnv_seg['chr'].replace(23, 'X').replace(24, 'Y').astype(str)

# Copy-number absolute counts
cnv = pd.read_csv('data/gdsc/copynumber/Gene_level_CN.txt', sep='\t', index_col=0)
cnv = cnv.loc[:, cnv.columns.isin(list(fc_sgrna))]
cnv_abs = cnv.applymap(lambda v: int(v.split(',')[0]))

# CIRSPR segments
crispr_seg = pd.read_csv('data/gdsc/crispr/segments_cbs_deseq2.csv')

# ccleanr
ccleanr = pd.read_csv('data/gdsc/crispr/all_GLCFC.csv', index_col=0)


# - Crispy corrected fold-changes
crispy_files = [f for f in os.listdir('data/crispy/') if f.startswith('crispy_gdsc_fold_change_gene_unsupervised_')]
fc_crispy = {os.path.splitext(f)[0].split('_')[6]: pd.read_csv('data/crispy/%s' % f, index_col=0) for f in crispy_files}

crispy_original = pd.DataFrame({i: fc_crispy[i]['original'] for i in fc_crispy})
crispy_corrected = pd.DataFrame({i: fc_crispy[i]['corrected'] for i in fc_crispy})


# - Essential genes AROCs
genes = set(crispy_original.index).intersection(ccleanr.index).intersection(crispy_corrected.index)
samples = set(crispy_original).intersection(ccleanr).intersection(crispy_corrected)
print(len(genes), len(samples))

res_auc = {}
for s in samples:
    res_auc[s] = {}
    for n, d in [('crispy', crispy_corrected), ('ccleanr', ccleanr), ('original', crispy_original)]:
        ax, ax_stats = plot_cumsum_auc(d[[s]], essential, legend=False)
        plt.close('all')
        res_auc[s][n] = ax_stats['auc'][s]
        print(s, n, ax_stats)

res_auc = pd.DataFrame(res_auc).T
print(res_auc.sort_values('ccleanr'))

# Plot
x1, x2, y = res_auc['original'], res_auc['ccleanr'], res_auc['crispy']

gs = GridSpec(1, 2, hspace=.6, wspace=.6)
for i, (x, y, xn, yn) in enumerate([(x1, y, 'Original FC', 'Crispy FC'), (x2, y, 'CCleanR FC', 'Crispy FC')]):
    ax = plt.subplot(gs[i])

    ax.scatter(x, y, c='#F2C500', s=3, marker='x', lw=0.5)
    sns.rugplot(x, height=.02, axis='x', c='#F2C500', lw=.3, ax=ax)
    sns.rugplot(y, height=.02, axis='y', c='#F2C500', lw=.3, ax=ax)

plt.suptitle('Essential genes AROC')
plt.gcf().set_size_inches(4, 1.5)
plt.savefig('reports/gdsc_essential_arocs.png', bbox_inches='tight', dpi=600)
plt.close('all')


# - Copy-number effect in non-expressed genes
plot_df = pd.concat([
    pd.concat([crispy_original.loc[nexp[i], i] for i in crispy_original if i in nexp], axis=1).unstack().rename('original'),
    pd.concat([crispy_corrected.loc[nexp[i], i] for i in crispy_corrected if i in nexp], axis=1).unstack().rename('crispy'),
    pd.concat([ccleanr.loc[nexp[i], i] for i in ccleanr if i in nexp], axis=1).unstack().rename('ccleanr'),
    cnv_abs.unstack().rename('cnv')
], axis=1).dropna().query('cnv != -1')

plot_df = plot_df.assign(cnv_d=['%d' % i if i < 10 else '10+' for i in plot_df['cnv']])

# Plot boxplots
order = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10+']

gs = GridSpec(3, 1, hspace=.3, wspace=.1)
for i, f in enumerate(['original', 'crispy', 'ccleanr']):
    ax = plt.subplot(gs[i])

    plot_cnv_rank(plot_df['cnv_d'], plot_df[f], stripplot=False, order=order, ax=ax)
    ax.set_ylabel(f.capitalize())

    if i == 0:
        ax.set_title('CNV effect non-expressed genes')

plt.gcf().set_size_inches(2.5, 3.5)
plt.savefig('reports/gdsc_cnv_effect_nexp.png', bbox_inches='tight', dpi=600)
plt.close('all')

# CCleanR scatter
g = sns.jointplot(
    plot_df['crispy'].rename('Crispy FC'), plot_df['ccleanr'].rename('CCleanR FC'), kind='reg', color='#37454B', space=0,
    marginal_kws={'hist': True, 'rug': False, 'kde': False, 'bins': 20}, annot_kws={'template': 'R={val:.2g}, p={p:.1e}', 'loc': 4},
    joint_kws={'scatter_kws': {'s': 2, 'edgecolor': 'w', 'linewidth': .3, 'alpha': .5}, 'line_kws': {'linewidth': .5}, 'truncate': True}
)
g.ax_joint.axhline(0, ls='-', lw=.1, c='#37454B')
g.ax_joint.axvline(0, ls='-', lw=.1, c='#37454B')
plt.gcf().set_size_inches(2, 2)
plt.savefig('reports/gdsc_ccleanr_scatter.png', bbox_inches='tight', dpi=600)
plt.close('all')


# - Chromossome plot
s, c = 'AU565', '17'

ghighlight = {'ERBB2'}

plot_df = fc_crispy[s].query("chrm == '%s'" % c)
plot_df = plot_df.assign(STARTpos=sgrna_lib.groupby('GENES')['STARTpos'].mean())

plot_chromosome(
    plot_df['STARTpos'], plot_df['original'].rename('Original FC'), plot_df['mean'].rename('Crispy FC'),
    seg=cnv_seg.query("(cellLine == '%s') & (chr == '%s')" % (s, c)),
    cytobands=cytobands.query("chr == 'chr%s'" % c),
    highlight=ghighlight, legend=True
)

plt.ylabel('')
plt.title('Sample: %s; Chr: %s; Var: %.2f' % (s, c, plot_df['var_rq'].mean()))
plt.gcf().set_size_inches(3, 1.5)
plt.savefig('reports/gdsc_chromossome_plot_%s_%s.png' % (s, c), bbox_inches='tight', dpi=600)
plt.close('all')

