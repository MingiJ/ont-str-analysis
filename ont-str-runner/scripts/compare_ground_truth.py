#!/usr/bin/env python3
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WARPSTR_ROOT = ROOT / 'work' / 'warpstr'
DEEP_ROOT = ROOT / 'work' / 'deeprepeat'
STRIQUE_ROOT = ROOT / 'work' / 'strique'
OUT_DIR = ROOT / 'work' / 'analysis'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / 'ground_truth_comparison.csv'

# Ground truth from CRISPR Cas9 Editing supplementary table (HTT CAG)
GROUND_TRUTH = {
    'GM04723': (72, 17),
    'ND30015': (41, 20),
    'ND30016': (41, 21),
    'ND30047': (41, 18),
    'ND30422': (40, 18),
    'ND30626': (41, 21),
    'ND31551': (39, 18),
    'ND33392': (57, 17),
    'ND33947': (40, 18),
}

SAMPLES = [
    'GM04723',
    'ND29970',
    'ND30015',
    'ND30016',
    'ND30047',
    'ND30422',
    'ND30626',
    'ND31551',
    'ND33392',
    'ND33947',
    'ND40534',
]


def read_alleles_csv(path: Path):
    with path.open() as f:
        row = next(csv.DictReader(f))
    def as_int(key):
        return int(row[key])
    return {
        'warp_a1': as_int('WarpSTR_allele1'),
        'warp_a1_freq': as_int('WarpSTR_allele1_freq'),
        'warp_a2': as_int('WarpSTR_allele2'),
        'warp_a2_freq': as_int('WarpSTR_allele2_freq'),
        'base_a1': as_int('basecall_allele1'),
        'base_a1_freq': as_int('basecall_allele1_freq'),
        'base_a2': as_int('basecall_allele2'),
        'base_a2_freq': as_int('basecall_allele2_freq'),
    }


def choose_peaks(a1, a2):
    return (max(a1, a2), min(a1, a2))


def approx_repeats(bp):
    # Assume counts are base pairs; convert to CAG repeats by dividing by 3.
    return int(round(bp / 3.0))


def read_overview_stats(path: Path):
    total = 0
    neg = 0
    high = 0
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            try:
                val = float(row['results'])
            except Exception:
                continue
            if val < 0:
                neg += 1
            if val > 300:
                high += 1
    return total, neg, high


def pick_deeprepeat_log(sample_dir: Path):
    if not sample_dir.exists():
        return None
    preferred = [sample_dir / 'htt_retry.log', sample_dir / 'htt.log']
    for p in preferred:
        if p.exists():
            return p
    # fallback: any log containing 'htt'
    logs = sorted(sample_dir.glob('*htt*.log'))
    return logs[0] if logs else None


def deeprepeat_stats(sample: str):
    sample_dir = DEEP_ROOT / sample
    log_path = pick_deeprepeat_log(sample_dir)
    fs_more = sample_dir / f'{sample}.fs.more.retry'
    if not fs_more.exists():
        fs_more = sample_dir / f'{sample}.fs.more'

    reads_reported = None
    warn_count = None
    repeat_info = None
    gmm_peaks = []
    allocr = {}
    allocr_top2 = []
    allocr_short_peak = None
    allocr_short_count = None
    allocr_long_peak = None
    allocr_long_count = None
    gmm_missed_short = None

    if log_path and log_path.exists():
        text = log_path.read_text(errors='ignore')
        m = re.search(r'There are\s+(\d+)\s+reads', text)
        if m:
            reads_reported = int(m.group(1))
        warn_count = text.count('Warning!!! less split points generated')
        repeat_info = text.count('Repeat Info:')
        # GMM peaks, e.g. "GMM: ND30047_htt-CAG [40, 43] allocr:..."
        m2 = re.search(r'GMM:.*?\[([^\]]+)\]', text)
        if m2:
            try:
                gmm_peaks = [int(x.strip()) for x in m2.group(1).split(',') if x.strip().isdigit()]
            except Exception:
                gmm_peaks = []
        # allocr distribution, e.g. "allocr:2:2, 4:3, ..."
        m3 = re.search(r'allocr:([^\n]+)', text)
        if m3:
            entries = m3.group(1).strip().rstrip(',')
            for part in entries.split(','):
                part = part.strip()
                if not part or ':' not in part:
                    continue
                k, v = part.split(':', 1)
                try:
                    allocr[int(k)] = int(v)
                except Exception:
                    continue
            # top 2 peaks by count
            allocr_top2 = sorted(allocr.items(), key=lambda x: x[1], reverse=True)[:2]
            # short/long mode heuristics for HTT CAG
            short_candidates = {k: v for k, v in allocr.items() if 15 <= k <= 25}
            long_candidates = {k: v for k, v in allocr.items() if 35 <= k <= 55}
            if short_candidates:
                allocr_short_peak = max(short_candidates.items(), key=lambda x: x[1])[0]
                allocr_short_count = short_candidates[allocr_short_peak]
            if long_candidates:
                allocr_long_peak = max(long_candidates.items(), key=lambda x: x[1])[0]
                allocr_long_count = long_candidates[allocr_long_peak]
            if allocr_short_count and allocr_long_count and gmm_peaks:
                short_ratio = allocr_short_count / float(allocr_short_count + allocr_long_count)
                # Flag if short mode is substantial but GMM peaks are all in long region.
                if short_ratio >= 0.2 and min(gmm_peaks) >= (allocr_short_peak + 8):
                    gmm_missed_short = True
                else:
                    gmm_missed_short = False

    fs_more_count = None
    if fs_more.exists():
        with fs_more.open() as f:
            fs_more_count = sum(1 for _ in f)

    return {
        'deeprepeat_log': str(log_path) if log_path else None,
        'deeprepeat_reads_reported': reads_reported,
        'deeprepeat_warn_count': warn_count,
        'deeprepeat_repeat_info': repeat_info,
        'deeprepeat_fs_more_count': fs_more_count,
        'deeprepeat_gmm_peaks': ",".join(str(x) for x in gmm_peaks) if gmm_peaks else None,
        'deeprepeat_allocr_top2': ";".join(f"{k}:{v}" for k, v in allocr_top2) if allocr_top2 else None,
        'deeprepeat_allocr_short_peak': allocr_short_peak,
        'deeprepeat_allocr_short_count': allocr_short_count,
        'deeprepeat_allocr_long_peak': allocr_long_peak,
        'deeprepeat_allocr_long_count': allocr_long_count,
        'deeprepeat_gmm_missed_short': gmm_missed_short,
    }


def strique_stats(sample: str):
    txt_path = STRIQUE_ROOT / f'{sample}.txt'
    if not txt_path.exists():
        return {
            'strique_txt': None,
            'strique_total': None,
            'strique_zero': None,
            'strique_high': None,
            'strique_filtered': None,
            'strique_peak_short': None,
            'strique_peak_short_reads': None,
            'strique_peak_long': None,
            'strique_peak_long_reads': None,
        }

    counts = []
    zero_count = 0
    high_count = 0
    with txt_path.open() as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('target') and row['target'] != 'HTT_CAG':
                continue
            try:
                val = int(float(row['count']))
            except Exception:
                continue
            counts.append(val)
            if val <= 0:
                zero_count += 1
            if val > 200:
                high_count += 1

    filtered = [c for c in counts if 1 <= c <= 200]
    hist = {}
    for c in filtered:
        hist[c] = hist.get(c, 0) + 1

    def peak_in_range(lo, hi):
        items = [(k, v) for k, v in hist.items() if lo <= k <= hi]
        if not items:
            return None, None
        # Choose the most frequent count; break ties by smaller repeat size.
        k, v = max(items, key=lambda x: (x[1], -x[0]))
        return k, v

    short_peak, short_reads = peak_in_range(10, 29)
    long_peak, long_reads = peak_in_range(30, 120)

    return {
        'strique_txt': str(txt_path),
        'strique_total': len(counts),
        'strique_zero': zero_count,
        'strique_high': high_count,
        'strique_filtered': len(filtered),
        'strique_peak_short': short_peak,
        'strique_peak_short_reads': short_reads,
        'strique_peak_long': long_peak,
        'strique_peak_long_reads': long_reads,
    }


rows = []
for sample in SAMPLES:
    truth = GROUND_TRUTH.get(sample)
    truth_long, truth_short = (truth if truth else (None, None))
    row = {
        'sample': sample,
        'truth_long': truth_long,
        'truth_short': truth_short,
    }

    alleles_path = WARPSTR_ROOT / sample / 'HTT_CAG' / 'predictions' / 'alleles.csv'
    overview_path = WARPSTR_ROOT / sample / 'HTT_CAG' / 'overview.csv'

    if alleles_path.exists():
        a = read_alleles_csv(alleles_path)
        warp_long, warp_short = choose_peaks(a['warp_a1'], a['warp_a2'])
        base_long, base_short = choose_peaks(a['base_a1'], a['base_a2'])

        row.update({
            'warp_peak_long': warp_long,
            'warp_peak_short': warp_short,
            'warp_peak_long_reads': a['warp_a1_freq'] if a['warp_a1'] == warp_long else a['warp_a2_freq'],
            'warp_peak_short_reads': a['warp_a1_freq'] if a['warp_a1'] == warp_short else a['warp_a2_freq'],
            'base_peak_long': base_long,
            'base_peak_short': base_short,
            'base_peak_long_reads': a['base_a1_freq'] if a['base_a1'] == base_long else a['base_a2_freq'],
            'base_peak_short_reads': a['base_a1_freq'] if a['base_a1'] == base_short else a['base_a2_freq'],
        })

        warp_long_rep = approx_repeats(warp_long)
        warp_short_rep = approx_repeats(warp_short)
        base_long_rep = approx_repeats(base_long)
        base_short_rep = approx_repeats(base_short)

        if truth_long is not None and truth_short is not None:
            warp_long_delta = warp_long_rep - truth_long
            warp_short_delta = warp_short_rep - truth_short
            base_long_delta = base_long_rep - truth_long
            base_short_delta = base_short_rep - truth_short
        else:
            warp_long_delta = None
            warp_short_delta = None
            base_long_delta = None
            base_short_delta = None

        row.update({
            'warp_long_rep': warp_long_rep,
            'warp_short_rep': warp_short_rep,
            'warp_long_delta': warp_long_delta,
            'warp_short_delta': warp_short_delta,
            'base_long_rep': base_long_rep,
            'base_short_rep': base_short_rep,
            'base_long_delta': base_long_delta,
            'base_short_delta': base_short_delta,
        })
    else:
        row.update({
            'warp_peak_long': None,
            'warp_peak_short': None,
            'warp_peak_long_reads': None,
            'warp_peak_short_reads': None,
            'base_peak_long': None,
            'base_peak_short': None,
            'base_peak_long_reads': None,
            'base_peak_short_reads': None,
            'warp_long_rep': None,
            'warp_short_rep': None,
            'warp_long_delta': None,
            'warp_short_delta': None,
            'base_long_rep': None,
            'base_short_rep': None,
            'base_long_delta': None,
            'base_short_delta': None,
        })

    if overview_path.exists():
        total, neg, high = read_overview_stats(overview_path)
        row.update({
            'warp_overview_total': total,
            'warp_overview_neg': neg,
            'warp_overview_high': high,
        })
    else:
        row.update({
            'warp_overview_total': None,
            'warp_overview_neg': None,
            'warp_overview_high': None,
        })

    row.update(deeprepeat_stats(sample))
    row.update(strique_stats(sample))

    strique_long = row.get('strique_peak_long')
    strique_short = row.get('strique_peak_short')
    if strique_long is not None:
        row['strique_long_rep'] = strique_long
        row['strique_long_delta'] = (strique_long - truth_long) if truth_long is not None else None
    else:
        row['strique_long_rep'] = None
        row['strique_long_delta'] = None

    if strique_short is not None:
        row['strique_short_rep'] = strique_short
        row['strique_short_delta'] = (strique_short - truth_short) if truth_short is not None else None
    else:
        row['strique_short_rep'] = None
        row['strique_short_delta'] = None

    rows.append(row)

# write csv
fieldnames = list(rows[0].keys())
with OUT_CSV.open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'Wrote {OUT_CSV}')
