from utils.formatting import to_decimal, round_decimal


def calculate_disposal_profit_loss(original_cost, accumulated_depreciation, sale_consideration,
                                    selling_expenses=0, places=2):
    original_cost = to_decimal(original_cost)
    accumulated_depreciation = to_decimal(accumulated_depreciation)
    sale_consideration = to_decimal(sale_consideration)
    selling_expenses = to_decimal(selling_expenses)

    net_book_value = original_cost - accumulated_depreciation
    net_sale_proceeds = sale_consideration - selling_expenses
    profit_loss = net_sale_proceeds - net_book_value

    if profit_loss > 0:
        p_type = "PROFIT ON SALE"
    elif profit_loss < 0:
        p_type = "LOSS ON SALE"
    else:
        p_type = "NIL"

    return {
        "net_book_value": round_decimal(net_book_value, places),
        "net_sale_proceeds": round_decimal(net_sale_proceeds, places),
        "profit_loss": round_decimal(abs(profit_loss), places),
        "profit_loss_type": p_type,
        "profit_loss_signed": round_decimal(profit_loss, places),
    }


def calculate_block_disposal_impact(sale_consideration, places=2):
    """
    Under the Income-tax block of assets concept, a disposed asset does NOT carry its
    own depreciation or WDV. The sale consideration simply reduces the WDV of the block
    to which the asset belonged. The actual tax effect (continuing depreciation, or a
    short-term capital gain if the block is extinguished/goes negative) is determined
    only when the block-level Income-tax depreciation is computed for the financial
    year in the Depreciation Run - not at the point of disposal itself.
    """
    return {"block_wdv_reduction": round_decimal(sale_consideration, places)}