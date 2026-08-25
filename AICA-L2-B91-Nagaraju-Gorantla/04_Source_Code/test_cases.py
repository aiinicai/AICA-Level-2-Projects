TEST_CASES = [

    {
        "id": "TC01",
        "name": "Standard Structured Email",
        "purpose": "Tests normal rule-based extraction.",
        "email": """
Subject: Additional Charges - SIM-0706-26 - ASLU7042918

Dear Sir,

Please find the additional charges:

Ferry Charges - USD 316
Demurrage Charges - USD 1790

Regards,
Demo User
""",
        "expected": {
            "file_reference": "SIM-0706-26",
            "container": "ASLU7042918",
            "total": 2106,
            "review": False,
        },
    },

    {
        "id": "TC02",
        "name": "Messy Natural Language",
        "purpose": "Demonstrates AI understanding of unstructured language.",
        "email": """
Subject: Extra recovery SIM-0999-26 MSCU1234567

pls recover from client 450 dollars being storage.
also there is 225 usd port penalty which client has to bear.
""",
        "expected": {
            "file_reference": "SIM-0999-26",
            "container": "MSCU1234567",
            "total": 675,
            "review": False,
        },
    },

    {
        "id": "TC03",
        "name": "Approximate Amount",
        "purpose": "Tests AI uncertainty and human-review control.",
        "email": """
Subject: Extra recovery SIM-0999-26 MSCU1234567

pls recover from client around 450 dollars being storage.
also there is 225 usd port penalty which client has to bear.
""",
        "expected": {
            "file_reference": "SIM-0999-26",
            "container": "MSCU1234567",
            "total": 675,
            "review": True,
        },
    },

    {
        "id": "TC04",
        "name": "Zero Amount",
        "purpose": "Confirms zero-value charges are ignored.",
        "email": """
Subject: Charges SIM-0801-26 TCLU7654321

Storage Charges USD 0
Demurrage Charges USD 600
Ferry Charges USD 200
""",
        "expected": {
            "file_reference": "SIM-0801-26",
            "container": "TCLU7654321",
            "total": 800,
            "review": False,
        },
    },

    {
        "id": "TC05",
        "name": "Missing Container",
        "purpose": "Tests mandatory-field validation.",
        "email": """
Subject: Additional Charges SIM-0810-26

Please recover USD 350 for warehouse rent.
""",
        "expected": {
            "file_reference": "SIM-0810-26",
            "container": None,
            "total": 350,
            "review": True,
        },
    },

    {
        "id": "TC06",
        "name": "Missing File Reference",
        "purpose": "Tests missing file-reference control.",
        "email": """
Subject: Additional container costs

Container CMAU1234567

Please recover detention charges of USD 700.
""",
        "expected": {
            "file_reference": None,
            "container": "CMAU1234567",
            "total": 700,
            "review": True,
        },
    },

    {
        "id": "TC07",
        "name": "Possible Duplicate Charge",
        "purpose": "Tests duplicate-charge validation.",
        "email": """
Subject: Extras SIM-0820-26 MEDU9876543

Storage Charges USD 300
Storage Charges USD 300
Demurrage Charges USD 500
""",
        "expected": {
            "file_reference": "SIM-0820-26",
            "container": "MEDU9876543",
            "total": 1100,
            "review": True,
        },
    },

    {
        "id": "TC08",
        "name": "Multiple Charge Types",
        "purpose": "Tests extraction of several additional costs.",
        "email": """
Subject: Additional Costs SIM-0830-26 TEMU1122334

Please charge customer:

Warehouse Rent USD 294
Ferry Charges USD 316
Demurrage USD 1790
Port Charges USD 125
""",
        "expected": {
            "file_reference": "SIM-0830-26",
            "container": "TEMU1122334",
            "total": 2525,
            "review": False,
        },
    },
]


def show_test_cases():

    print()
    print("=" * 72)
    print("AICA LEVEL 2 CAPSTONE - TEST CASE REGISTER")
    print("=" * 72)

    for test in TEST_CASES:

        print()
        print(
            test["id"],
            "-",
            test["name"]
        )

        print(
            "Purpose:",
            test["purpose"]
        )

        print(
            "Expected Total:",
            "USD",
            f'{test["expected"]["total"]:,.2f}'
        )

        print(
            "Expected Review:",
            test["expected"]["review"]
        )

        print("-" * 72)


if __name__ == "__main__":

    show_test_cases()