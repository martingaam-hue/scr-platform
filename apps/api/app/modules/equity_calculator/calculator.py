"""Pure deterministic equity calculations. No LLM, no DB."""


def calculate_scenario(
    pre_money_valuation: float,
    investment_amount: float,
    shares_outstanding_before: int,
    security_type: str = "common_equity",
    liquidation_preference: float | None = None,
    participation_cap: float | None = None,
    anti_dilution_type: str = "none",
) -> dict:
    """
    Compute equity scenario metrics deterministically.

    Returns dict with:
    - post_money_valuation, equity_percentage, new_shares_issued, price_per_share
    - cap_table: [{"name": "Existing Shareholders", "shares": N, "percentage": X, "investment": None},
                  {"name": "New Investor", "shares": M, "percentage": Y, "investment": Z}]
    - waterfall: list of WaterfallScenario dicts for 1x, 1.5x, 2x, 3x, 5x, 10x exit multiples
    - dilution_impact: {"pre_investment_ownership": X, "post_investment_ownership": Y, "dilution_percentage": Z}
    """
    if pre_money_valuation <= 0:
        raise ValueError("pre_money_valuation must be positive")
    if investment_amount <= 0:
        raise ValueError("investment_amount must be positive")
    if shares_outstanding_before <= 0:
        raise ValueError("shares_outstanding_before must be positive")

    post_money = pre_money_valuation + investment_amount
    equity_pct = investment_amount / post_money
    price_per_share = pre_money_valuation / shares_outstanding_before
    new_shares = round(investment_amount / price_per_share)
    total_shares = shares_outstanding_before + new_shares

    existing_pct = round(shares_outstanding_before / total_shares * 100, 2)
    investor_pct = round(equity_pct * 100, 2)

    cap_table = [
        {
            "name": "Existing Shareholders",
            "shares": shares_outstanding_before,
            "percentage": existing_pct,
            "investment": None,
        },
        {
            "name": "New Investor",
            "shares": new_shares,
            "percentage": investor_pct,
            "investment": investment_amount,
        },
    ]

    # Waterfall at multiples
    multiples = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    waterfall = []
    for m in multiples:
        exit_val = post_money * m

        if security_type == "preferred_equity" and liquidation_preference and liquidation_preference > 0:
            # Liquidation preference paid first (capped at exit value)
            liq = min(liquidation_preference, exit_val)
            remaining = exit_val - liq
            if participation_cap and participation_cap > 0:
                # Participating preferred with cap
                investor_participation = remaining * equity_pct
                max_additional = max(0.0, participation_cap - liq)
                investor_participation = min(investor_participation, max_additional)
            else:
                # Non-participating: choose better of liquidation pref or pro-rata conversion
                conversion_proceeds = exit_val * equity_pct
                if conversion_proceeds > liq:
                    # Convert to common
                    investor_proceeds = conversion_proceeds
                else:
                    investor_proceeds = liq
                    investor_participation = 0.0
                    founder_proceeds = max(0.0, exit_val - investor_proceeds)
                    moic = investor_proceeds / investment_amount if investment_amount else 0.0
                    waterfall.append({
                        "multiple": m,
                        "exit_value": round(exit_val, 2),
                        "investor_proceeds": round(investor_proceeds, 2),
                        "founder_proceeds": round(founder_proceeds, 2),
                        "investor_moic": round(moic, 3),
                        "investor_irr_estimate": None,
                    })
                    continue
            investor_proceeds = liq + investor_participation
        elif security_type in ("convertible_note", "safe"):
            # Simplified: treat as equity at post-money valuation
            investor_proceeds = exit_val * equity_pct
        else:
            # Common equity — pure pro-rata
            investor_proceeds = exit_val * equity_pct

        founder_proceeds = max(0.0, exit_val - investor_proceeds)
        moic = investor_proceeds / investment_amount if investment_amount else 0.0
        waterfall.append({
            "multiple": m,
            "exit_value": round(exit_val, 2),
            "investor_proceeds": round(investor_proceeds, 2),
            "founder_proceeds": round(founder_proceeds, 2),
            "investor_moic": round(moic, 3),
            "investor_irr_estimate": None,
        })

    dilution_impact = {
        "pre_investment_ownership": 100.0,
        "post_investment_ownership": round((1.0 - equity_pct) * 100, 2),
        "dilution_percentage": round(equity_pct * 100, 2),
        "anti_dilution_protection": anti_dilution_type not in ("none", ""),
        "anti_dilution_type": anti_dilution_type,
        "total_shares_after": total_shares,
        "new_shares_issued": new_shares,
    }

    return {
        "post_money_valuation": post_money,
        "equity_percentage": round(equity_pct * 100, 4),
        "new_shares_issued": new_shares,
        "price_per_share": round(price_per_share, 6),
        "cap_table": cap_table,
        "waterfall": waterfall,
        "dilution_impact": dilution_impact,
    }
