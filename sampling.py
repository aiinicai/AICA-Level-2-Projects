"""Reproducible simple random sample selection for audit documentation."""
from __future__ import annotations

from datetime import datetime
import pandas as pd


def simple_random_sample(population: pd.DataFrame, sample_size: int, seed: int) -> tuple[pd.DataFrame, dict, str]:
    """Pick rows using a user-set seed."""
    if population.empty:
        return population.copy(), {}, "No population available."
    size = min(max(int(sample_size), 1), len(population))
    sample = population.sample(n=size, random_state=int(seed)).copy()
    params = {
        "Method": "Simple random sampling", "Parameters": f"Size={size}, Seed={seed}",
        "Items": len(sample), "Value": float(sample["Amount"].sum()),
    }
    note = f"Simple random sampling: {size} items selected from {len(population)} rows using seed {seed}."
    return sample, params, note

def select_key_items(population: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, dict, str]:
    sample = population[population["Amount"] >= threshold].copy()
    params = {
        "Method": "Key items (100% testing)", "Parameters": f"Threshold >= ₹{threshold:,.2f}",
        "Items": len(sample), "Value": float(sample["Amount"].sum()),
    }
    note = f"Key items: All {len(sample)} items with value >= ₹{threshold:,.2f} selected for 100% testing."
    return sample, params, note

def stratified_sample(population: pd.DataFrame, bands: list[float], samples_per_band: int, seed: int) -> tuple[pd.DataFrame, dict, str]:
    if population.empty: return population.copy(), {}, ""
    df = population.copy()
    sorted_bands = sorted(bands)
    labels = [f"Up to {sorted_bands[0]:,.0f}"] + [f"{sorted_bands[i]:,.0f} to {sorted_bands[i+1]:,.0f}" for i in range(len(sorted_bands)-1)] + [f"Above {sorted_bands[-1]:,.0f}"]
    bins = [-float('inf')] + sorted_bands + [float('inf')]
    df["Strata"] = pd.cut(df["Amount"], bins=bins, labels=labels)
    
    samples = []
    for label in labels:
        subset = df[df["Strata"] == label]
        if not subset.empty:
            s_size = min(len(subset), samples_per_band)
            samples.append(subset.sample(n=s_size, random_state=seed))
    
    sample = pd.concat(samples).copy()
    params = {
        "Method": "Stratified sampling", "Parameters": f"Bands={bands}, n/band={samples_per_band}",
        "Items": len(sample), "Value": float(sample["Amount"].sum()),
    }
    note = f"Stratified sampling: Selected {samples_per_band} items from each value band where available."
    return sample, params, note

def monetary_unit_sample(population: pd.DataFrame, 
                          tolerable_misstatement: float, 
                          confidence_level: float, 
                          expected_misstatement: float,
                          seed: int = 42) -> tuple[pd.DataFrame, dict, str]:
    """Basic MUS (Fixed Interval Sampling) implementation."""
    df = population.copy().sort_values("Amount", ascending=False)
    # Simple risk factor calculation for demonstration (Audit standards vary)
    risk_factor = {0.80: 1.61, 0.90: 2.31, 0.95: 3.00}.get(confidence_level, 3.0)
    
    total_value = df["Amount"].sum()
    # Sampling Interval = (Tolerable - Expected) / Risk Factor (Simplified)
    interval = max((tolerable_misstatement - expected_misstatement) / risk_factor, 1.0)
    
    df["CumSum"] = df["Amount"].cumsum()
    # Systematic selection starting from a random point in first interval
    import numpy as np
    rng = np.random.default_rng(seed)
    start_point = rng.uniform(0, interval)
    
    points = np.arange(start_point, total_value, interval)
    selected_indices = []
    for p in points:
        idx = df[df["CumSum"] >= p].index
        if not idx.empty:
            selected_indices.append(idx[0])
            
    sample = df.loc[list(set(selected_indices))].copy()
    params = {
        "Method": "Monetary Unit Sampling (MUS)", 
        "Parameters": f"Interval=₹{interval:,.2f}, Conf={confidence_level*100}%",
        "Items": len(sample), "Value": float(sample["Amount"].sum()),
    }
    note = f"MUS: Population value ₹{total_value:,.2f} sampled at interval ₹{interval:,.2f}."
    return sample, params, note
