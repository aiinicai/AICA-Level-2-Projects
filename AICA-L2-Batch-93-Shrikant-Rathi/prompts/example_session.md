# Example session: committee questions to Claude through MCP

| Question to Claude | Tools Claude calls | Output in `examples/mcp_tool_outputs.json` |
|---|---|---|
| Who and what is in the portfolio? | `list_entities` | 5 entities, 12 schemes, policy limits |
| How is the family doing overall? | `portfolio_summary` | Rs 47.17 cr, XIRR 7.96% |
| What do we really own once funds are looked through? | `look_through_exposure` | HDFC Bank 12.56% of equity; 501 companies, all 12 funds looked through |
| Are we within the investment policy? | `policy_check` | 2 breaches, 3 overlap warnings, 1 not computable |
| How similar are our two large-cap funds? | `fund_overlap` | 54.56% overlap, 38 common stocks |
| How has Parag Parikh Flexi Cap performed? | `fund_report` | Returns, risk metrics, top holdings |
| What are HDFC Bank's fundamentals and our exposure? | `company_report` | Ratios, 5 years of statements, exposure, data caveat |
| What is the HUF's capital-gains position? | `tax_position` | Indicative, Income-tax Act, 2025, ss. 196 and 198 |
| What if the market falls 20%? | `stress_test` | -Rs 8.74 cr (-19.21% of equity, beta 0.96) |
| Where did the data come from? | `data_provenance` | Sources, AMC files with SHA-256, warnings |
| *Use the ic_note prompt: is the family over-exposed to HDFC Bank?* | all of the above + `verify_note` | [sample_ic_note.md](../examples/sample_ic_note.md) |
