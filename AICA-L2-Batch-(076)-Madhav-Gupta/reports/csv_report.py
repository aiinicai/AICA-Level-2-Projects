def export_dataframe_to_csv(df, filepath):
    df.to_csv(filepath, index=False)
    return filepath