import logging
import numpy as np
import pandas as pd
import re
import warnings

logger = logging.getLogger('root')

def extract_features(fast5_dir: str, f5c_eventalign_file: str, region: str, results: str):
    logger.info("Extracting features from " + f5c_eventalign_file + " file...")
    chr, start, end = re.split(r'[:-]', region)
    start, end = int(start), int(end)

    df = pd.DataFrame()
    for chunk in pd.read_csv(f5c_eventalign_file, sep='\t', chunksize=50000):
        filtered_df = chunk.query('contig == @chr and position >= @start and position <= @end')
        df = pd.concat([df, filtered_df])

    df = df.head(10000)  # to speed up calculations, should be removed in PROD environment

    logger.info("Number of rows after filtering: " + str(df.shape[0]))
    unique_reads = list(set(df['read_name']))
    logger.info("Number of unique reads after filtering: " + str(len(unique_reads)))

    logger.info("Creating new dataframe with features...")
    result_df = pd.DataFrame()
    for unique_read in unique_reads:
        for pos in range(start, end, 1):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                samples = df.query('read_name == @unique_read and position == @pos')
                samples_string = ','.join(samples["samples"].values.tolist())
                samples_list = [float(i) for i in samples_string.split(',')] if samples_string != '' else []
                event_length_list = samples["event_length"].values.tolist()
                result_df = pd.concat([result_df, pd.DataFrame([{"read_name": unique_read, "position": pos, "samples": samples_list, "mean_samples": np.mean(samples_list), "event_length": event_length_list, "sum_event_length": np.sum(event_length_list) }])], ignore_index=True)

    result_df['mean_samples'] = result_df['mean_samples'].fillna(0)
    logger.info("Number of rows in features table: " + str(result_df.shape[0]))

    return unique_reads, result_df
