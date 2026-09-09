import pandas as pd


def asset_register_dataframe(conn):
    query = """SELECT a.asset_id, a.asset_name, c.category_name, c.category_code, a.purchase_date,
                      a.original_cost, a.opening_accum_dep, a.status, a.companies_act_method,
                      a.department, a.location
               FROM assets a JOIN asset_categories c ON a.category_id = c.category_id
               ORDER BY a.asset_id"""
    return pd.read_sql_query(query, conn)


def depreciation_run_dataframe(conn, run_id):
    query = """SELECT dr.asset_id, a.asset_name, c.category_code, dr.companies_act_depreciation,
                      dr.closing_carrying_amount, tb.block_code, br.depreciation as block_depreciation,
                      br.deferred_tax, br.deferred_tax_type
               FROM depreciation_records dr
               JOIN assets a ON dr.asset_id = a.asset_id
               JOIN asset_categories c ON a.category_id = c.category_id
               LEFT JOIN tax_blocks tb ON a.income_tax_block_id = tb.block_id
               LEFT JOIN tax_block_records br ON br.run_id = dr.run_id AND br.block_id = a.income_tax_block_id
               WHERE dr.run_id = ?"""
    return pd.read_sql_query(query, conn, params=(run_id,))


def deferred_tax_dataframe(conn, financial_year=None):
    query = """SELECT tb.block_name, tb.block_code, br.closing_carrying_amount_total,
                      br.closing_wdv as tax_base, br.temporary_difference,
                      br.deferred_tax_rate as tax_rate, br.deferred_tax, br.deferred_tax_type
               FROM tax_block_records br
               JOIN tax_blocks tb ON br.block_id = tb.block_id
               JOIN depreciation_runs r ON br.run_id = r.run_id
               WHERE r.status='POSTED'"""
    params = []
    if financial_year:
        query += " AND br.financial_year = ?"
        params.append(financial_year)
    return pd.read_sql_query(query, conn, params=params)


def disposal_dataframe(conn):
    query = """SELECT d.asset_id, a.asset_name, a.purchase_date, d.disposal_date, d.original_cost,
                      d.accumulated_depreciation, d.net_book_value, d.sale_consideration,
                      d.selling_expenses, d.net_sale_proceeds, d.profit_loss, d.profit_loss_type
               FROM disposal_records d JOIN assets a ON d.asset_id = a.asset_id"""
    return pd.read_sql_query(query, conn)