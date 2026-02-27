"""Pre-built legal template definitions with questionnaire sections."""

from typing import Any

# Each template: id, name, doc_type, description, questionnaire_sections
# Field types: text, textarea, select, number, date, boolean, group(conditional)

SYSTEM_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "nda_standard",
        "name": "Non-Disclosure Agreement (NDA)",
        "doc_type": "nda",
        "description": "Standard bilateral NDA protecting confidential information during deal discussions.",
        "estimated_pages": 4,
        "questionnaire": {
            "sections": [
                {
                    "id": "parties",
                    "title": "Parties",
                    "fields": [
                        {"id": "disclosing_party", "type": "text", "label": "Disclosing Party Name", "required": True},
                        {"id": "receiving_party", "type": "text", "label": "Receiving Party Name", "required": True},
                        {"id": "governing_law", "type": "select", "label": "Governing Law / Jurisdiction",
                         "options": ["England & Wales", "New York", "Delaware", "Singapore", "Netherlands", "France", "Germany", "Other"],
                         "required": True},
                    ],
                },
                {
                    "id": "scope",
                    "title": "Scope & Duration",
                    "fields": [
                        {"id": "purpose", "type": "textarea", "label": "Purpose of Disclosure", "required": True,
                         "placeholder": "e.g., Evaluation of potential investment in renewable energy project"},
                        {"id": "duration_years", "type": "select", "label": "Confidentiality Period",
                         "options": ["1 year", "2 years", "3 years", "5 years", "Indefinite"], "required": True},
                        {"id": "nda_type", "type": "select", "label": "NDA Type",
                         "options": ["Mutual (both parties)", "One-way (disclosing party only)"], "required": True},
                    ],
                },
            ],
        },
        "template_text": (
            "NON-DISCLOSURE AGREEMENT\n\n"
            "This Non-Disclosure Agreement (\"Agreement\") is entered into between {{disclosing_party}} "
            "and {{receiving_party}} (collectively, the \"Parties\") for the purpose of {{purpose}}.\n\n"
            "The confidentiality obligations under this Agreement shall remain in effect for {{duration_years}} "
            "from the date of signing. This Agreement is governed by the laws of {{governing_law}}.\n\n"
            "[AI will complete remaining standard clauses including definitions, obligations, exclusions, "
            "remedies, and termination provisions.]"
        ),
    },
    {
        "id": "term_sheet_equity",
        "name": "Term Sheet (Equity Investment)",
        "doc_type": "term_sheet",
        "description": "Standard VC/PE term sheet for equity investments with key deal terms.",
        "estimated_pages": 6,
        "questionnaire": {
            "sections": [
                {
                    "id": "deal_basics",
                    "title": "Deal Basics",
                    "fields": [
                        {"id": "company_name", "type": "text", "label": "Company / Project Name", "required": True},
                        {"id": "investor_name", "type": "text", "label": "Investor Name", "required": True},
                        {"id": "investment_amount", "type": "number", "label": "Investment Amount (USD)", "required": True},
                        {"id": "pre_money_valuation", "type": "number", "label": "Pre-Money Valuation (USD)", "required": True},
                        {"id": "security_type", "type": "select", "label": "Security Type",
                         "options": ["Common Equity", "Preferred Equity", "Convertible Note", "SAFE"], "required": True},
                    ],
                },
                {
                    "id": "key_terms",
                    "title": "Key Terms",
                    "fields": [
                        {"id": "liquidation_preference", "type": "select", "label": "Liquidation Preference",
                         "options": ["1x non-participating", "1x participating", "2x non-participating", "None"]},
                        {"id": "anti_dilution", "type": "select", "label": "Anti-Dilution Protection",
                         "options": ["Broad-based weighted average", "Narrow-based weighted average", "Full ratchet", "None"]},
                        {"id": "board_seats", "type": "number", "label": "Board Seats for Investor"},
                        {"id": "pro_rata_rights", "type": "boolean", "label": "Pro-Rata Rights?"},
                        {"id": "information_rights", "type": "boolean", "label": "Information Rights?"},
                    ],
                },
                {
                    "id": "conditions",
                    "title": "Conditions Precedent",
                    "fields": [
                        {"id": "conditions", "type": "textarea", "label": "Conditions to Closing",
                         "placeholder": "e.g., Satisfactory due diligence, regulatory approvals, audited financials"},
                        {"id": "closing_date", "type": "date", "label": "Expected Closing Date"},
                        {"id": "governing_law", "type": "select", "label": "Governing Law",
                         "options": ["Delaware", "England & Wales", "New York", "Singapore", "Other"]},
                    ],
                },
            ],
        },
        "template_text": (
            "TERM SHEET\n\nNon-Binding — Subject to Definitive Documentation\n\n"
            "Company: {{company_name}}\nInvestor: {{investor_name}}\n"
            "Investment Amount: ${{investment_amount}}\nPre-Money Valuation: ${{pre_money_valuation}}\n"
            "Security Type: {{security_type}}\n\n"
            "KEY TERMS\nLiquidation Preference: {{liquidation_preference}}\n"
            "Anti-Dilution: {{anti_dilution}}\nBoard Seats: {{board_seats}}\n\n"
            "[AI will complete: governance, ROFR/co-sale rights, drag-along, representations, and closing conditions.]"
        ),
    },
    {
        "id": "subscription_agreement",
        "name": "Subscription Agreement",
        "doc_type": "subscription_agreement",
        "description": "LP subscription agreement for fund or SPV investment commitments.",
        "estimated_pages": 12,
        "questionnaire": {
            "sections": [
                {
                    "id": "investor_details",
                    "title": "Investor Details",
                    "fields": [
                        {"id": "investor_name", "type": "text", "label": "Investor Legal Name", "required": True},
                        {"id": "investor_type", "type": "select", "label": "Investor Type",
                         "options": ["Individual", "Corporate", "Fund", "Trust", "Other"], "required": True},
                        {"id": "investor_address", "type": "textarea", "label": "Investor Address", "required": True},
                        {"id": "commitment_amount", "type": "number", "label": "Capital Commitment (USD)", "required": True},
                    ],
                },
                {
                    "id": "fund_details",
                    "title": "Fund / SPV Details",
                    "fields": [
                        {"id": "fund_name", "type": "text", "label": "Fund / SPV Name", "required": True},
                        {"id": "gp_name", "type": "text", "label": "General Partner / Manager", "required": True},
                        {"id": "management_fee_pct", "type": "number", "label": "Management Fee (%)"},
                        {"id": "carried_interest_pct", "type": "number", "label": "Carried Interest (%)"},
                        {"id": "preferred_return_pct", "type": "number", "label": "Preferred Return / Hurdle Rate (%)"},
                    ],
                },
                {
                    "id": "representations",
                    "title": "Investor Representations",
                    "fields": [
                        {"id": "accredited_investor", "type": "boolean", "label": "Accredited Investor?", "required": True},
                        {"id": "qualified_purchaser", "type": "boolean", "label": "Qualified Purchaser?"},
                        {"id": "us_person", "type": "boolean", "label": "US Person (for Regulation S)?"},
                        {"id": "source_of_funds", "type": "select", "label": "Source of Funds",
                         "options": ["Own funds", "Institutional capital", "Pension fund", "Endowment", "Other"]},
                    ],
                },
            ],
        },
        "template_text": (
            "SUBSCRIPTION AGREEMENT\n\n"
            "{{fund_name}} (the \"Fund\")\nManaged by {{gp_name}} (the \"General Partner\")\n\n"
            "Investor: {{investor_name}} ({{investor_type}})\n"
            "Capital Commitment: ${{commitment_amount}}\n\n"
            "Management Fee: {{management_fee_pct}}% | Carried Interest: {{carried_interest_pct}}%\n"
            "Preferred Return: {{preferred_return_pct}}%\n\n"
            "[AI will complete: capital call mechanics, drawdown schedule, transfer restrictions, "
            "ERISA provisions, tax representations, and signature blocks.]"
        ),
    },
    {
        "id": "loi",
        "name": "Letter of Intent (LOI)",
        "doc_type": "term_sheet",
        "description": "Non-binding or binding letter of intent for investment or acquisition.",
        "estimated_pages": 3,
        "questionnaire": {
            "sections": [
                {
                    "id": "basics",
                    "title": "Transaction Basics",
                    "fields": [
                        {"id": "buyer_name", "type": "text", "label": "Buyer / Investor Name", "required": True},
                        {"id": "target_name", "type": "text", "label": "Target / Project Name", "required": True},
                        {"id": "transaction_type", "type": "select", "label": "Transaction Type",
                         "options": ["Equity Investment", "Asset Acquisition", "Loan / Debt", "Partnership", "Other"]},
                        {"id": "indicative_price", "type": "text", "label": "Indicative Price / Valuation"},
                        {"id": "binding_status", "type": "select", "label": "Binding Status",
                         "options": ["Non-binding (indicative)", "Binding LOI", "Partially binding (exclusivity binding)"]},
                    ],
                },
                {
                    "id": "timeline",
                    "title": "Timeline & Exclusivity",
                    "fields": [
                        {"id": "exclusivity_days", "type": "number", "label": "Exclusivity Period (days)"},
                        {"id": "dd_period_days", "type": "number", "label": "Due Diligence Period (days)"},
                        {"id": "target_close_date", "type": "date", "label": "Target Signing Date"},
                    ],
                },
            ],
        },
        "template_text": (
            "LETTER OF INTENT\n\n"
            "From: {{buyer_name}}\nTo: {{target_name}}\n\n"
            "Re: {{transaction_type}} — {{indicative_price}}\n\n"
            "This {{binding_status}} letter of intent outlines the proposed terms of the above transaction. "
            "Exclusivity period: {{exclusivity_days}} days. Due diligence period: {{dd_period_days}} days.\n\n"
            "[AI will complete: transaction overview, conditions, representations, and next steps.]"
        ),
    },
    {
        "id": "side_letter",
        "name": "Side Letter",
        "doc_type": "side_letter",
        "description": "Investor-specific side letter granting special rights or terms.",
        "estimated_pages": 3,
        "questionnaire": {
            "sections": [
                {
                    "id": "basics",
                    "title": "Parties & Fund",
                    "fields": [
                        {"id": "investor_name", "type": "text", "label": "Investor Name", "required": True},
                        {"id": "fund_name", "type": "text", "label": "Fund / SPV Name", "required": True},
                        {"id": "gp_name", "type": "text", "label": "General Partner", "required": True},
                    ],
                },
                {
                    "id": "special_terms",
                    "title": "Special Terms",
                    "fields": [
                        {"id": "mfn_clause", "type": "boolean", "label": "Most Favoured Nation (MFN) Clause?"},
                        {"id": "fee_discount", "type": "text", "label": "Fee Discount (if any)"},
                        {"id": "reporting_frequency", "type": "select", "label": "Reporting Frequency",
                         "options": ["Monthly", "Quarterly", "Annual", "Standard"]},
                        {"id": "coinvestment_rights", "type": "boolean", "label": "Co-Investment Rights?"},
                        {"id": "transfer_rights", "type": "select", "label": "Transfer Rights",
                         "options": ["Standard", "Enhanced (with GP consent only)", "Free transfer to affiliates"]},
                        {"id": "additional_terms", "type": "textarea", "label": "Additional Special Terms"},
                    ],
                },
            ],
        },
        "template_text": (
            "SIDE LETTER AGREEMENT\n\n"
            "Between: {{fund_name}} (managed by {{gp_name}}) and {{investor_name}} (\"the Investor\")\n\n"
            "This Side Letter supplements the subscription agreement between the parties and grants "
            "the Investor the following special terms:\n\n"
            "{{additional_terms}}\n\n"
            "[AI will complete: specific rights, carve-outs, conflict provisions, and signature block.]"
        ),
    },
]

REVIEW_MODES = {
    "comprehensive": "Full clause-by-clause analysis with risk scoring",
    "risk_focused": "Highlight high-risk clauses and missing protections",
    "compliance": "Check against regulatory requirements for jurisdiction",
    "negotiation": "Identify negotiation leverage points and alternatives",
}

SUPPORTED_JURISDICTIONS = [
    "England & Wales", "New York", "Delaware", "Singapore",
    "Netherlands", "Germany", "France", "Cayman Islands",
    "British Virgin Islands", "Luxembourg", "Ireland", "Other",
]
