#!/usr/bin/env python3
"""
fetch_forecasts.py - Data Verification and Fetch Script for TASK D4 (Round 4)

This script validates and verifies the integrity of ex-ante astrologer forecasts,
classical Sanskrit text scans (Brihat Samhita and Brihat Parasara Hora Sastra),
and post-hoc claims delivered in research/incoming/forecasts/round4/.

It computes SHA-256 checksums for all round4 datasets and verifies live availability
of key primary archive endpoints on Internet Archive and the Wayback Machine.

Requirements: Python 3.8+ (Standard Library only; no paid API keys required).
"""

import csv
import hashlib
import json
import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DELIVERABLES = [
    'forecasts.csv',
    'post_hoc.csv',
    'text_pages.csv',
    'sources.csv'
]

KEY_ARCHIVE_ENDPOINTS = [
    ("Brihat Samhita (Bhat 1981)", "https://archive.org/metadata/brihatsamhitawithenglishtranslationramakrishnabhattm.part1mlbd_305_s"),
    ("Brihat Parasara Hora Sastra (Santhanam 1992)", "https://archive.org/metadata/BPHSEnglish"),
    ("Astrological Musings Ex-Ante 2016 Snapshot", "https://archive.org/wayback/available?url=https://astrologicalmusings.com/hindu-new-year-chart-2016-and-forecast-for-india/"),
    ("The Astrological Magazine Vol 79 Jan 1990", "https://archive.org/metadata/njqv_the-astrological-magazine-editor-bangalore-venkata-raman-astrology-magazine"),
    ("SSGEOS Turkey Quake Ex-Ante Tweet", "https://archive.org/wayback/available?url=https://twitter.com/hogrbe/status/1621479563720118273")
]

def sha256_file(filepath):
    """Compute SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def check_deliverable_integrity():
    """Verify presence, row count, and checksum of local deliverable CSVs."""
    print("=" * 70)
    print("TASK D4 DELIVERABLE INTEGRITY AND CHECKSUMS")
    print("=" * 70)
    all_ok = True
    for fname in DELIVERABLES:
        fpath = os.path.join(BASE_DIR, fname)
        if not os.path.exists(fpath):
            print(f"[FAIL] Missing deliverable: {fname}")
            all_ok = False
            continue
        size = os.path.getsize(fpath)
        sha = sha256_file(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
            row_count = len(rows)
        print(f"File: {fname}")
        print(f"  Size:      {size:,} bytes")
        print(f"  Rows:      {row_count} records (excluding header)")
        print(f"  Columns:   {len(header)}")
        print(f"  SHA-256:   {sha}")
        print()
    return all_ok

def check_archive_connectivity():
    """Verify live connectivity and HTTP 200 responses from primary archive endpoints."""
    print("=" * 70)
    print("LIVE PRIMARY ARCHIVE ENDPOINT PROBES")
    print("=" * 70)
    headers = {'User-Agent': 'Mozilla/5.0 (Vedic-Astrology-Scientific-Research-Bot/1.0)'}
    for label, url in KEY_ARCHIVE_ENDPOINTS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                data = json.loads(resp.read().decode('utf-8'))
                print(f"[OK] {label}")
                print(f"     URL:    {url}")
                print(f"     Status: HTTP {status}")
                if 'archived_snapshots' in data:
                    snap = data.get('archived_snapshots', {}).get('closest', {})
                    print(f"     Latest Snapshot: {snap.get('timestamp')} ({snap.get('url')})")
                elif 'metadata' in data:
                    print(f"     Title:  {data.get('metadata', {}).get('title')}")
                print()
        except Exception as e:
            print(f"[WARN] {label} probe failed: {e}")
            print(f"       URL: {url}\n")

def analyze_forecast_distribution():
    """Print breakdown of forecasts by topic and year."""
    fc_path = os.path.join(BASE_DIR, 'forecasts.csv')
    if not os.path.exists(fc_path):
        return
    topic_counts = {}
    year_counts = {}
    with open(fc_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            top = row['topic']
            topic_counts[top] = topic_counts.get(top, 0) + 1
            yr = row['window_start'][:4]
            year_counts[yr] = year_counts.get(yr, 0) + 1

    print("=" * 70)
    print("FORECAST DISTRIBUTION SUMMARY")
    print("=" * 70)
    print("Counts by Topic:")
    for top, cnt in sorted(topic_counts.items()):
        print(f"  - {top.capitalize():<12}: {cnt} forecasts")
    print("\nCounts by Year:")
    for yr, cnt in sorted(year_counts.items()):
        print(f"  - {yr}: {cnt} forecasts")
    print("=" * 70)

if __name__ == '__main__':
    integrity = check_deliverable_integrity()
    analyze_forecast_distribution()
    check_archive_connectivity()
    if not integrity:
        sys.exit(1)
