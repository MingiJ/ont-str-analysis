import os
import argparse
from index import convert_reference_to_signal
from extract_features import extract_features
from map import map_fast5_reads_to_reference_signal
from plot import plot_signal, plot_time_histogram, plot_time_per_read
from collections import Counter
import log

logger = log.setup_custom_logger('root')

def main():
    parser = argparse.ArgumentParser(description="main")
    parser.add_argument("--fast5_dir", type=str, help="Path to the directory with fast5 files.")
    parser.add_argument("--f5c_eventalign_file", type=str, help="Path to the output of the f5c eventalign file.")
    parser.add_argument("--region", type=str, help="The region under consideration, e.g. chr1:1000-5000")
    parser.add_argument("--kmer_model", type=str, help="Kmer model based on pore model used in sequencing process.")
    parser.add_argument("--kmer_length", type=int, help="Kmer length.")
    parser.add_argument("--motif", type=str, help="Motif.")
    parser.add_argument("--min_motif_repeat_counts", type=int, help="Minimum motif repeat counts to check.")
    parser.add_argument("--max_motif_repeat_counts", type=int, help="Minimum motif repeat counts to check.")
    parser.add_argument("--draw", type=bool, help="If should draw", default=False)
    parser.add_argument("--results", type=str, help="Path to the results dir.")
    args = parser.parse_args()
    logger.info(f"f5c eventalign fast5_dir file: {args.fast5_dir}")
    logger.info(f"results dir: {args.results}")

    if not os.path.exists(args.results):
        os.makedirs(args.results)
        logger.info("The new directory " + args.results + " is created!")

    reference_signal = convert_reference_to_signal(args.kmer_model, args.kmer_length, args.motif, args.min_motif_repeat_counts, args.max_motif_repeat_counts)
    repeat_counts_dict = map_fast5_reads_to_reference_signal(args.fast5_dir, reference_signal, args.results, args.f5c_eventalign_file, args.region, args.draw)
    repeat_counts = [int(a_dict['ref_id']) for a_dict in repeat_counts_dict]
    freq_counter = Counter(repeat_counts)
    print(freq_counter)
    # unique_reads, features = extract_features(args.fast5_dir, args.f5c_eventalign_file, args.region, args.results)
    # plot_signal(unique_reads, features, args.results)
    # plot_time_per_read(unique_reads, features, 10, args.results)
    # plot_time_histogram(unique_reads, features, args.results)

if __name__ == "__main__":
    main()
