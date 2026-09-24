"""
Unit tests for CertificateClassifier.
Verifies accurate classification of Acts (1961 vs 2025) and Form types.
"""

import pytest
from core.classifier import CertificateClassifier
from config import ACT_1961, ACT_2025, CATEGORY_TDS, CATEGORY_TCS


@pytest.fixture
def classifier():
    return CertificateClassifier()


def test_classify_form_16a_1961(classifier):
    sample_text = (
        "FORM NO. 16A\n[See rule 31(1)(b)]\n"
        "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source\n"
        "on payments other than salary\n"
        "Name and address of the Deductee: TATA CONSULTANCY SERVICES LIMITED\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "16A"
    assert name == "Form 16A"
    assert act == ACT_1961
    assert category == CATEGORY_TDS
    assert conf >= 0.5


def test_classify_form_16_1961(classifier):
    sample_text = (
        "FORM NO. 16\n[See rule 31(1)(a)]\n"
        "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on salary\n"
        "Part A\nName of Employee: RAHUL ARVIND DESHMUKH\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "16"
    assert name == "Form 16"
    assert act == ACT_1961
    assert category == CATEGORY_TDS
    assert conf >= 0.5


def test_classify_form_27d_1961(classifier):
    sample_text = (
        "FORM NO. 27D\n[See rule 37D]\n"
        "Certificate under section 206C of the Income-tax Act, 1961 for tax collected at source\n"
        "Name and address of the Collectee: JINDAL STEEL LIMITED\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "27D"
    assert name == "Form 27D"
    assert act == ACT_1961
    assert category == CATEGORY_TCS
    assert conf >= 0.5


def test_classify_form_16b_1961(classifier):
    sample_text = (
        "FORM NO. 16B\n[See rule 31(1)(c)]\n"
        "Certificate under section 194-IA of the Income-tax Act, 1961\n"
        "Name and address of the Transferor: PRIYA MEHTA\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "16B"
    assert name == "Form 16B"
    assert act == ACT_1961


def test_classify_form_130_2025(classifier):
    sample_text = (
        "FORM NO. 130\n"
        "Certificate for Tax Deducted at Source on Salary under the Income-tax Act, 2025\n"
        "Name of Employee: VIKRAM NARENDRA PATEL\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "130"
    assert name == "Form 130"
    assert act == ACT_2025
    assert category == CATEGORY_TDS
    assert conf >= 0.5


def test_classify_form_131_2025(classifier):
    sample_text = (
        "FORM NO. 131\n"
        "Certificate for Tax Deducted at Source on Non-Salary Payments under the Income-tax Act, 2025\n"
        "Name of Deductee: HCL TECHNOLOGIES\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "131"
    assert name == "Form 131"
    assert act == ACT_2025
    assert category == CATEGORY_TDS


def test_classify_form_133_2025(classifier):
    sample_text = (
        "FORM NO. 133\n"
        "Certificate for Tax Collected at Source under the Income-tax Act, 2025\n"
        "Name of Collectee: ROYAL MOTORS\n"
    )
    code, name, act, category, conf = classifier.classify(sample_text)
    assert code == "133"
    assert name == "Form 133"
    assert act == ACT_2025
    assert category == CATEGORY_TCS


def test_classify_empty_text(classifier):
    code, name, act, category, conf = classifier.classify("")
    assert code == "UNKNOWN"
    assert conf == 0.0
