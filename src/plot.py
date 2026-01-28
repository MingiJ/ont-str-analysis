import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import os, re

logger = logging.getLogger('root')

def plot_signal(unique_reads, features, results: str):
    logger.info("Ploting signal for " + str(len(unique_reads)) + " reads...")

    results = results + '/img/signal'
    if not os.path.exists(results):
        os.makedirs(results)
        logger.info("The new directory " + results + " is created!")

    for unique_read in unique_reads:
        features_for_read = features.query('read_name == @unique_read')
        features_for_read.columns = ['read_name', 'position', 'samples', 'mean_samples', 'event_length', 'sum_event_length']
        
        plt.figure(figsize=(25,9))
        sns.lineplot(data=features_for_read, x="position", y="mean_samples", hue="read_name")
        plt.savefig(results + '/mean_samples_' + unique_read + '.png')
        plt.close()
    return

def plot_time_per_read(unique_reads, features, window_size: int, results: str):
    logger.info("Ploting speed for " + str(len(unique_reads)) + " reads...")

    results = results + '/img/time'
    if not os.path.exists(results):
        os.makedirs(results)
        logger.info("The new directory " + results + " is created!")

    for unique_read in unique_reads:
        features_for_read = features.query('read_name == @unique_read')
        features_for_read.columns = ['read_name', 'position', 'samples', 'mean_samples', 'event_length', 'sum_event_length']
        features_for_read['mean_in_window_event_length'] = features_for_read.sum_event_length.rolling(window_size, min_periods=2, center=True).mean()
        
        plt.figure(figsize=(25,9))
        sns.lineplot(data=features_for_read, x="position", y="mean_in_window_event_length", hue="read_name")
        plt.savefig(results + '/speed_' + unique_read + '.png')
        plt.close()
    return

def plot_time_histogram(unique_reads, features, results: str):
    logger.info("Ploting time for " + str(len(unique_reads)) + " reads...")

    results = results + '/img/time'
    if not os.path.exists(results):
        os.makedirs(results)
        logger.info("The new directory " + results + " is created!")

    times_list = []
    for unique_read in unique_reads:
        features_for_read = features.query('read_name == @unique_read')
        features_for_read.columns = ['read_name', 'position', 'samples', 'mean_samples', 'event_length', 'sum_event_length']
        times_list.append(np.sum(features_for_read['sum_event_length'])) 
    counts, bins = np.histogram(times_list, bins=100)
    plt.figure(figsize=(25,9))
    plt.hist(bins[:-1], bins, weights=counts)
    plt.savefig(results + '/time_histogram.png')
    plt.close()
    return
