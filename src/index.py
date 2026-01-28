import logging
import numpy as np
import pandas as pd
import re
import warnings

from Bio import SeqIO

logger = logging.getLogger('root')

def convert_reference_to_signal(kmer_model: str, kmer_length: int, motif: str, min_motif_repeat_counts: int, max_motif_repeat_counts: int):
    logger.info("Building kmer model from " + kmer_model + " file...")
    df = pd.DataFrame()
    for chunk in pd.read_csv(kmer_model, sep='\t', chunksize=50000):
        df = pd.concat([df, chunk])
    kmer_map = df.set_index('kmer').T.to_dict('dict')
    logger.info("Kmer model built from " + str(len(kmer_map)) + " kmers")
    signals = {}
    for motif_repeat_count in range(min_motif_repeat_counts, max_motif_repeat_counts):
        seq = motif * motif_repeat_count
        if len(seq) <= kmer_length:
            continue
        k = len(seq) - kmer_length
        signal = []
        for i in range(k):
            kmer = seq[i:i+kmer_length]
            kmer_signal = kmer_map[kmer.upper()]['level_mean']
            signal.append(kmer_signal)
        signals[motif_repeat_count] = signal
    logger.info("Properly converted " + str(len(signals)) + " sequences")
    return signals
