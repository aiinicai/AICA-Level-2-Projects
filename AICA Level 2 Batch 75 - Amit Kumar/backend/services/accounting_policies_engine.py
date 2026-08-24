from sqlalchemy.orm import Session
from models import Client, AccountingPolicy

STANDARD_POLICIES = [
    {
        "number": "AP-01",
        "title": "Basis of preparation",
        "template": "The financial statements have been prepared in accordance with Generally Accepted Accounting Principles in India (Indian GAAP) under the historical cost convention on an accrual basis. The financial statements comply in all material respects with the Accounting Standards specified under Section 133 of the Companies Act, 2013, read with Rule 7 of the Companies (Accounts) Rules, 2014, and the relevant provisions of the Companies Act, 2013, including Schedule III Division I."
    },
    {
        "number": "AP-02",
        "title": "Use of estimates",
        "template": "The preparation of financial statements in conformity with Indian GAAP requires management to make estimates and assumptions that affect the reported amounts of assets and liabilities, disclosures of contingent liabilities as at the date of financial statements, and the reported amounts of revenues and expenses during the reporting period. Actual results could differ from those estimates. Any revision to accounting estimates is recognized prospectively in current and future periods."
    },
    {
        "number": "AP-03",
        "title": "Property, plant and equipment",
        "template": "Property, plant and equipment are stated at cost of acquisition or construction less accumulated depreciation and accumulated impairment losses, if any. The cost comprises purchase price, borrowing costs if capitalization criteria are met, and directly attributable costs of bringing the asset to its working condition for intended use. Subsequent expenditure relating to property, plant and equipment is capitalized only when it increases the future economic benefits from the asset."
    },
    {
        "number": "AP-04",
        "title": "Capital work-in-progress",
        "template": "Capital work-in-progress (CWIP) includes cost of property, plant and equipment that are not ready for their intended use as at the reporting date. CWIP is carried at cost, comprising direct costs, attributable borrowing costs, and directly allocated expenses incurred during the construction/erection period. Capital advances given towards acquisition of fixed assets are disclosed under long-term loans and advances."
    },
    {
        "number": "AP-05",
        "title": "Depreciation and amortisation",
        "template": "Depreciation on property, plant and equipment is provided on the Straight Line Method (SLM) based on the useful lives of assets prescribed under Schedule II of the Companies Act, 2013. Intangible assets are amortized over their estimated useful economic life on a straight-line basis, not exceeding five years. Assets costing individually up to Rs 5,000 are fully depreciated in the year of acquisition."
    },
    {
        "number": "AP-06",
        "title": "Impairment of assets",
        "template": "The carrying amounts of assets are reviewed at each Balance Sheet date to determine whether there is any indication of impairment. If any such indication exists, the asset's recoverable amount is estimated. An impairment loss is recognized whenever the carrying amount of an asset exceeds its recoverable amount. Recoverable amount is the higher of net selling price and value in use."
    },
    {
        "number": "AP-07",
        "title": "Inventories",
        "template": "Inventories are valued at the lower of cost and net realizable value. Cost of raw materials, components, stores and spares is determined on First-In-First-Out (FIFO) basis. Cost of finished goods and work-in-progress includes direct material, direct labor, and an appropriate proportion of fixed and variable overheads incurred in bringing inventories to their present location and condition."
    },
    {
        "number": "AP-08",
        "title": "Revenue recognition",
        "template": "Revenue is recognized to the extent that it is probable that the economic benefits will flow to the Company and revenue can be reliably measured. Revenue from domestic and export sale of goods is recognized upon transfer of significant risks and rewards of ownership to the buyer, which generally coincides with dispatch or delivery of goods. Sales are net of trade discounts, returns, GST, and applicable indirect taxes."
    },
    {
        "number": "AP-09",
        "title": "Other income",
        "template": "Interest income is recognized on a time proportion basis taking into account the amount outstanding and the applicable interest rate. Dividend income is recognized when the right to receive payment is established by the balance sheet date. Profit or loss on sale of investments is recognized on trade date basis."
    },
    {
        "number": "AP-10",
        "title": "Employee benefits",
        "template": "Short-term employee benefits are recognized as an expense in the Statement of Profit and Loss for the year in which services are rendered. Post-employment benefits such as Provident Fund and ESIC are defined contribution plans and charged to Profit and Loss as incurred. Gratuity and Leave Encashment liabilities are defined benefit obligations determined based on actuarial valuation as at the year end."
    },
    {
        "number": "AP-11",
        "title": "Borrowing costs",
        "template": "Borrowing costs directly attributable to the acquisition, construction, or production of qualifying assets are capitalized as part of the cost of such asset until the asset is substantially ready for its intended use. A qualifying asset is one that necessarily takes a substantial period of time to get ready for its intended use. Other borrowing costs are recognized as an expense in the period in which they are incurred."
    },
    {
        "number": "AP-12",
        "title": "Foreign currency transactions",
        "template": "Foreign currency transactions are recorded at exchange rates prevailing on the date of transaction. Monetary assets and liabilities denominated in foreign currencies as at reporting date are translated at exchange rates prevailing at balance sheet date. Exchange differences arising on settlement or translation of monetary items are recognized as income or expense in the Statement of Profit and Loss."
    },
    {
        "number": "AP-13",
        "title": "Taxation",
        "template": "Tax expense comprises current tax and deferred tax. Current tax is measured at the amount expected to be paid to the tax authorities in accordance with the provisions of the Income Tax Act, 1961. Minimum Alternate Tax (MAT) paid in accordance with tax laws is recognized as an asset when it is probable that future economic benefit will flow to the Company."
    },
    {
        "number": "AP-14",
        "title": "Deferred tax",
        "template": "Deferred tax is recognized on timing differences between taxable income and accounting income originating in one period and capable of reversal in one or more subsequent periods. Deferred tax assets are recognized only to the extent there is reasonable certainty that sufficient future taxable income will be available against which such deferred tax assets can be realized."
    },
    {
        "number": "AP-15",
        "title": "Provisions and contingent liabilities",
        "template": "A provision is recognized when the Company has a present obligation as a result of past events and it is probable that an outflow of resources will be required to settle the obligation. Contingent liabilities are not recognized but are disclosed in the notes to accounts when there is a possible obligation or present obligation where outflow is not probable. Contingent assets are neither recognized nor disclosed."
    },
    {
        "number": "AP-16",
        "title": "Investments",
        "template": "Investments that are readily realizable and intended to be held for not more than a year from the reporting date are classified as current investments and carried at lower of cost and fair value. Long-term investments are carried at cost. Provision for diminution in value of long-term investments is made only if such decline is of other than temporary nature."
    },
    {
        "number": "AP-17",
        "title": "Cash and cash equivalents",
        "template": "Cash and cash equivalents in the balance sheet comprise cash at bank, cash in hand, and short-term fixed deposits with an original maturity of three months or less that are readily convertible to known amounts of cash and subject to insignificant risk of changes in value."
    },
    {
        "number": "AP-18",
        "title": "Earnings per share",
        "template": "Basic earnings per share is computed by dividing net profit or loss after tax attributable to equity shareholders by the weighted average number of equity shares outstanding during the year. Diluted earnings per share is computed after adjusting for effects of all dilutive potential equity shares."
    },
    {
        "number": "AP-19",
        "title": "Related party disclosures",
        "template": "Disclosures as required under AS 18 Related Party Disclosures are made in respect of transactions with parties that are related to the Company by virtue of control, significant influence, or key management personnel relationship."
    },
    {
        "number": "AP-20",
        "title": "Leases",
        "template": "Leases where the lessor effectively retains substantially all risks and benefits of ownership are classified as operating leases. Operating lease payments are recognized as an expense in the Statement of Profit and Loss on a straight-line basis over the lease term."
    },
    {
        "number": "AP-21",
        "title": "Previous year comparatives and regrouping",
        "template": "Previous year figures have been regrouped, reclassified, and rearranged wherever necessary to conform with the current year's presentation and Schedule III Division I classification requirements."
    }
]


def generate_or_update_accounting_policies(client_id: int, db: Session):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return []

    existing_policies = {p.policy_number: p for p in db.query(AccountingPolicy).filter(AccountingPolicy.client_id == client_id).all()}

    for std in STANDARD_POLICIES:
        num = std["number"]
        base_text = std["template"]
        title = std["title"]

        if num in existing_policies:
            pol_obj = existing_policies[num]
            pol_obj.suggested_content = base_text
            if not pol_obj.is_modified:
                pol_obj.content = base_text
        else:
            pol_obj = AccountingPolicy(
                client_id=client_id,
                policy_number=num,
                title=title,
                content=base_text,
                suggested_content=base_text,
                is_applicable=True,
                is_modified=False
            )
            db.add(pol_obj)

    db.commit()
    return db.query(AccountingPolicy).filter(AccountingPolicy.client_id == client_id).all()
