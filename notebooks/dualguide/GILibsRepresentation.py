import numpy as np
import pandas as pd
import pkg_resources
import seaborn as sns
from crispy import logger as LOG
import matplotlib.pyplot as plt
from dualguide import read_gi_library
from crispy.CrispyPlot import CrispyPlot
from crispy.LibRepresentationReport import LibraryRepresentaion

DPATH = pkg_resources.resource_filename("data", "dualguide/")
RPATH = pkg_resources.resource_filename("notebooks", "dualguide/reports/")

if __name__ == "__main__":
    # Samplesheet
    #
    lib_ss = pd.read_excel(f"{DPATH}/gi_samplesheet.xlsx")

    # lib_name, lib_ss_df = list(lib_ss.groupby("library"))[0]
    for lib_name, lib_ss_df in lib_ss.groupby("library"):
        LOG.info(f"{lib_name}")

        lib = read_gi_library(lib_name)

        samples = list(set(lib_ss_df["name"]))
        samples_pal = lib_ss_df.groupby("name")["palette"].first()

        # Counts
        #
        counts_df = pd.read_excel(
            f"{DPATH}/{lib_name}_samples_counts.xlsx", index_col=0
        )
        counts_df = counts_df.reindex(lib.index).replace(np.nan, 0).astype(int)

        # Library representation reports
        #
        lib_report = LibraryRepresentaion(counts_df)

        # Comparison gini scores
        #
        gini_scores_comparison = dict(
            avana=0.361, brunello=0.291, yusa_v1=0.342, yusa_v11=0.229
        )

        gini_scores_comparison_palette = dict(
            avana="#66c2a5", brunello="#fc8d62", yusa_v1="#8da0cb", yusa_v11="#e78ac3"
        )

        gini_scores = (
            lib_report.gini()
            .reset_index()
            .rename(columns={"index": "sample", 0: "gini"})
        )

        # Gini scores barplot
        #
        plt.figure(figsize=(2.5, len(samples) * 0.3), dpi=600)

        sns.barplot(
            "gini",
            "sample",
            data=gini_scores,
            orient="h",
            order=samples,
            palette=samples_pal,
            saturation=1,
            lw=0,
        )

        plt.grid(True, ls="-", lw=0.1, alpha=1.0, zorder=0, axis="x")

        for k, v in gini_scores_comparison.items():
            plt.axvline(
                v, lw=0.5, zorder=1, color=gini_scores_comparison_palette[k], label=k
            )

        plt.xlabel("Gini score")
        plt.ylabel("")

        plt.legend(
            frameon=False, loc="center left", bbox_to_anchor=(1, 0.5), prop={"size": 4}
        )

        plt.savefig(f"{RPATH}/{lib_name}_gini_barplot.pdf", bbox_inches="tight")
        plt.close("all")

        # Lorenz curves
        #
        lib_report.lorenz_curve(palette=samples_pal)
        plt.gcf().set_size_inches(2, 2)
        plt.savefig(
            f"{RPATH}/{lib_name}_lorenz_curve.pdf", bbox_inches="tight", dpi=600
        )
        plt.close("all")

        # sgRNA counts boxplots
        #
        lib_report.boxplot(palette=samples_pal)
        plt.gcf().set_size_inches(1.5, 1.5)
        plt.savefig(
            f"{RPATH}/{lib_name}_counts_boxplots.pdf", bbox_inches="tight", dpi=600
        )
        plt.close("all")

        # sgRNA counts histograms
        #
        lib_report.distplot(palette=samples_pal)
        plt.gcf().set_size_inches(2.5, 2)
        plt.savefig(f"{RPATH}/{lib_name}_counts_histograms.pdf", bbox_inches="tight")
        plt.close("all")

        # Percentile scores barplot (good library will have a value below 6)
        #
        percentile_scores = (
            lib_report.percentile()
            .reset_index()
            .rename(columns={"index": "sample", 0: "range"})
        )

        plt.figure(figsize=(2.5, 1.0), dpi=600)

        sns.barplot(
            "range",
            "sample",
            data=percentile_scores,
            orient="h",
            order=samples,
            palette=samples_pal,
            saturation=1,
            lw=0,
        )

        plt.grid(True, ls="-", lw=0.1, alpha=1.0, zorder=0, axis="x")

        plt.axvline(6, lw=0.5, zorder=1, color="k")

        plt.xlabel("Fold-change range containing 95% of the guides")
        plt.ylabel("")

        plt.savefig(f"{RPATH}/{lib_name}_fc_range_barplot.pdf", bbox_inches="tight")
        plt.close("all")

        # Drop-out rates barplot
        #
        dropout_thres = np.arange(0, 40, 5)
        dropout_palette = pd.Series(sns.light_palette(CrispyPlot.PAL_DTRACE[1], n_colors=len(dropout_thres)).as_hex(), index=dropout_thres)
        dropout_rates = pd.concat(
            [
                (lib_report.dropout_rate(threshold=t) * 100)
                .rename("dropout")
                .reset_index()
                .assign(thres=t)
                for t in dropout_thres
            ],
            ignore_index=True,
        )

        plt.figure(figsize=(2.5, 1.0), dpi=600)

        ax = sns.barplot(
            "dropout",
            "index",
            "thres",
            data=dropout_rates,
            orient="h",
            order=samples,
            palette=dropout_palette,
            saturation=1,
            lw=0,
        )

        plt.grid(True, ls="-", lw=0.1, alpha=1.0, zorder=0, axis="x")

        vals = ax.get_xticks()
        ax.set_xticklabels([f"{x:.1f}%" for x in vals])

        plt.xlabel("Dropout sgRNAs (zero counts)")
        plt.ylabel("")

        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), frameon=False, prop={"size": 6}, title="counts <=")

        plt.savefig(f"{RPATH}/{lib_name}_dropout_barplot.pdf", bbox_inches="tight")
        plt.close("all")
