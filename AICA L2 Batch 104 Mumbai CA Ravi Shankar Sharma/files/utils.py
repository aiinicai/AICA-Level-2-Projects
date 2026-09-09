import pandas as pd
from datetime import timedelta

def reconcile_transactions(bank_df, gl_df, date_tolerance=3, amount_tolerance=0):
    """
    Reconcile bank and GL transactions.
    
    Returns: matched, bank_only, gl_only, mismatch, duplicates DataFrames
    """
    
    bank_df = bank_df.copy()
    gl_df = gl_df.copy()
    
    # Add tracking columns
    bank_df['Matched'] = False
    bank_df['Source'] = 'Bank'
    gl_df['Matched'] = False
    gl_df['Source'] = 'GL'
    
    matched_list = []
    mismatch_list = []
    duplicates_set = set()
    
    # Find duplicates in bank statement
    bank_duplicates = bank_df[bank_df.duplicated(subset=['Date', 'Amount', 'Reference'], keep=False)]
    bank_dup_indices = set(bank_duplicates.index)
    
    # Find duplicates in GL register
    gl_duplicates = gl_df[gl_df.duplicated(subset=['Date', 'Amount', 'Reference'], keep=False)]
    gl_dup_indices = set(gl_duplicates.index)
    
    # Try to match transactions
    for b_idx, bank_row in bank_df.iterrows():
        best_match = None
        best_score = -1
        best_gl_idx = None
        
        if b_idx in bank_dup_indices:
            continue  # Handle duplicates separately
        
        for g_idx, gl_row in gl_df.iterrows():
            if g_idx in gl_dup_indices or gl_df.loc[g_idx, 'Matched']:
                continue
            
            # Amount match (exact)
            if bank_row['Amount'] != gl_row['Amount']:
                continue
            
            # Date match (within tolerance)
            date_diff = abs((bank_row['Date'] - gl_row['Date']).days)
            if date_diff > date_tolerance:
                continue
            
            # Reference or Description match
            ref_match = False
            if pd.notna(bank_row['Reference']) and pd.notna(gl_row['Reference']):
                if str(bank_row['Reference']).strip() == str(gl_row['Reference']).strip():
                    ref_match = True
            
            # Score: prefer exact date match and reference match
            score = 0
            if date_diff == 0:
                score += 2
            if ref_match:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = gl_row
                best_gl_idx = g_idx
        
        # Record match if found
        if best_match is not None and best_score >= 0:
            bank_df.loc[b_idx, 'Matched'] = True
            gl_df.loc[best_gl_idx, 'Matched'] = True
            
            matched_record = {
                'Bank_Date': bank_row['Date'],
                'GL_Date': best_match['Date'],
                'Reference': bank_row['Reference'],
                'Amount': bank_row['Amount'],
                'Date_Diff_Days': abs((bank_row['Date'] - best_match['Date']).days)
            }
            matched_list.append(matched_record)
    
    # Find mismatches (same reference but different amounts/dates)
    for b_idx, bank_row in bank_df.iterrows():
        if bank_row['Matched'] or b_idx in bank_dup_indices:
            continue
        
        for g_idx, gl_row in gl_df.iterrows():
            if gl_df.loc[g_idx, 'Matched'] or g_idx in gl_dup_indices:
                continue
            
            # Check if reference matches
            ref_match = False
            if pd.notna(bank_row['Reference']) and pd.notna(gl_row['Reference']):
                if str(bank_row['Reference']).strip() == str(gl_row['Reference']).strip():
                    ref_match = True
            
            if ref_match:
                mismatch_record = {
                    'Bank_Date': bank_row['Date'],
                    'Bank_Amount': bank_row['Amount'],
                    'GL_Date': gl_row['Date'],
                    'GL_Amount': gl_row['Amount'],
                    'Reference': bank_row['Reference'],
                    'Amount_Diff': abs(bank_row['Amount'] - gl_row['Amount']),
                    'Date_Diff_Days': abs((bank_row['Date'] - gl_row['Date']).days)
                }
                mismatch_list.append(mismatch_record)
                bank_df.loc[b_idx, 'Matched'] = True
                gl_df.loc[g_idx, 'Matched'] = True
                break
    
    # Build result DataFrames
    matched_df = pd.DataFrame(matched_list)
    mismatch_df = pd.DataFrame(mismatch_list)
    
    bank_only = bank_df[~bank_df['Matched']].copy()
    gl_only = gl_df[~gl_df['Matched']].copy()
    
    # Get duplicates
    bank_dup_df = bank_df[bank_df.index.isin(bank_dup_indices)].copy()
    bank_dup_df['Type'] = 'Bank'
    gl_dup_df = gl_df[gl_df.index.isin(gl_dup_indices)].copy()
    gl_dup_df['Type'] = 'GL'
    duplicates = pd.concat([bank_dup_df, gl_dup_df], ignore_index=True)
    
    return (
        matched_df if len(matched_df) > 0 else pd.DataFrame(),
        bank_only[['Date', 'Reference', 'Amount', 'Balance']],
        gl_only[['Date', 'Reference', 'Amount', 'Description']],
        mismatch_df if len(mismatch_df) > 0 else pd.DataFrame(),
        duplicates if len(duplicates) > 0 else pd.DataFrame()
    )


def generate_brs(bank_df, matched, bank_only, gl_only, mismatch):
    """Generate Bank Reconciliation Statement summary."""
    
    bank_balance = bank_df['Balance'].iloc[-1] if len(bank_df) > 0 else 0
    
    gl_total = bank_df['Amount'].sum()
    
    # Calculate GL book balance
    gl_book_balance = gl_total
    
    # Adjustments for BRS
    brs_data = {
        'Particulars': [
            'Balance as per Bank Statement',
            'Add: Cheques in transit',
            'Less: Deposits in transit',
            'Balance as per GL'
        ],
        'Amount': [
            bank_balance,
            0 if len(bank_only) == 0 else bank_only[bank_only['Amount'] > 0]['Amount'].sum(),
            0 if len(bank_only) == 0 else abs(bank_only[bank_only['Amount'] < 0]['Amount'].sum()),
            gl_book_balance
        ]
    }
    
    return pd.DataFrame(brs_data)
