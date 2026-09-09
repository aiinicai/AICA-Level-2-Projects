package com.example.core.util

import com.example.core.database.AppDatabase
import com.example.core.model.AccountEntity
import com.example.core.model.BusinessEntity
import com.example.core.model.CategoryEntity
import com.example.core.model.PartyEntity
import com.example.core.model.PaymentMode
import com.example.core.model.TransactionEntity
import com.example.core.model.TransactionType
import java.util.UUID

object SeedData {
    suspend fun populateInitialData(database: AppDatabase) {
        val defaultBusiness = database.businessDao().getDefaultBusiness()
        if (defaultBusiness != null) return // Already initialized

        val businessId = UUID.randomUUID().toString()
        val business = BusinessEntity(
            id = businessId,
            name = "Sharma Electricals",
            ownerName = "Ramesh Sharma",
            businessType = "Electrical & Hardware",
            phone = "+91 98765 43210",
            gstin = "07AAAAA0000A1Z5",
            pan = "AAAAA0000A",
            currencyCode = "INR",
            upiId = "sharmaelectricals@upi",
            address = "Shop 12, Main Market, Chandni Chowk, Delhi",
            isDefault = true
        )
        database.businessDao().insertBusiness(business)

        // Accounts
        val cashAccId = UUID.randomUUID().toString()
        val bankAccId = UUID.randomUUID().toString()
        val upiAccId = UUID.randomUUID().toString()

        database.accountDao().insertAccount(
            AccountEntity(
                id = cashAccId,
                businessId = businessId,
                name = "Cash in Hand",
                type = "CASH",
                openingBalancePaise = 2500000L // ₹25,000.00
            )
        )
        database.accountDao().insertAccount(
            AccountEntity(
                id = bankAccId,
                businessId = businessId,
                name = "HDFC Current A/C",
                type = "BANK",
                accountNumber = "50200012345678",
                ifscCode = "HDFC0001234",
                openingBalancePaise = 14500000L // ₹1,45,000.00
            )
        )
        database.accountDao().insertAccount(
            AccountEntity(
                id = upiAccId,
                businessId = businessId,
                name = "Shop QR UPI",
                type = "UPI",
                upiId = "sharmaelectricals@upi",
                openingBalancePaise = 1850000L // ₹18,500.00
            )
        )

        // Categories
        val rentCat = CategoryEntity(businessId = businessId, name = "Shop Rent", iconName = "store", isExpense = true, isDefault = true)
        val salaryCat = CategoryEntity(businessId = businessId, name = "Staff Salary", iconName = "badge", isExpense = true, isDefault = true)
        val elecCat = CategoryEntity(businessId = businessId, name = "Electricity Bill", iconName = "bolt", isExpense = true, isDefault = true)
        val transportCat = CategoryEntity(businessId = businessId, name = "Goods Transport", iconName = "local_shipping", isExpense = true, isDefault = true)
        val miscCat = CategoryEntity(businessId = businessId, name = "Tea & Refreshment", iconName = "coffee", isExpense = true, isDefault = true)
        database.categoryDao().insertCategories(listOf(rentCat, salaryCat, elecCat, transportCat, miscCat))

        // Parties
        val now = System.currentTimeMillis()
        val dayMs = 24 * 60 * 60 * 1000L

        val rajTradersId = UUID.randomUUID().toString()
        val mehtaHardwareId = UUID.randomUUID().toString()
        val kumarElectId = UUID.randomUUID().toString()
        val nehaServicesId = UUID.randomUUID().toString()
        val vermaBuildersId = UUID.randomUUID().toString()

        val rajTraders = PartyEntity(
            id = rajTradersId,
            businessId = businessId,
            name = "Raj Traders",
            phone = "9810123456",
            address = "Sector 18, Noida",
            gstin = "09ABCDE1234F1Z5",
            roles = "CUSTOMER",
            notes = "Wholesale customer for LED lights & wires",
            createdAt = now - (45 * dayMs),
            updatedAt = now - (2 * dayMs)
        )
        val mehtaHardware = PartyEntity(
            id = mehtaHardwareId,
            businessId = businessId,
            name = "Mehta Hardware",
            phone = "9820234567",
            address = "Loha Mandi, Delhi",
            gstin = "07BCDEF2345G1Z6",
            roles = "SUPPLIER",
            notes = "Main supplier for switches and copper conduits",
            createdAt = now - (60 * dayMs),
            updatedAt = now - (5 * dayMs)
        )
        val kumarElect = PartyEntity(
            id = kumarElectId,
            businessId = businessId,
            name = "Kumar Electricals",
            phone = "9830345678",
            address = "Karol Bagh, Delhi",
            roles = "CUSTOMER,SUPPLIER",
            notes = "Dual role: supplies PVC pipes, buys industrial wires",
            createdAt = now - (95 * dayMs),
            updatedAt = now - (1 * dayMs)
        )
        val nehaServices = PartyEntity(
            id = nehaServicesId,
            businessId = businessId,
            name = "Neha Contractor Services",
            phone = "9840456789",
            address = "Cyber City, Gurugram",
            roles = "CUSTOMER",
            notes = "Commercial electrical installation contractor",
            createdAt = now - (15 * dayMs),
            updatedAt = now - (3 * dayMs)
        )
        val vermaBuilders = PartyEntity(
            id = vermaBuildersId,
            businessId = businessId,
            name = "Verma Builders",
            phone = "9850567890",
            address = "Greater Kailash, Delhi",
            roles = "CUSTOMER",
            notes = "Residential project developer",
            createdAt = now - (110 * dayMs),
            updatedAt = now - (20 * dayMs)
        )

        database.partyDao().insertParty(rajTraders)
        database.partyDao().insertParty(mehtaHardware)
        database.partyDao().insertParty(kumarElect)
        database.partyDao().insertParty(nehaServices)
        database.partyDao().insertParty(vermaBuilders)

        // Transactions
        // 1. Raj Traders: Credit given ₹45,000, Got ₹20,000 -> Net ₹25,000 Receivable
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = rajTradersId,
                accountId = cashAccId,
                type = TransactionType.GAVE.name,
                amountPaise = 4500000L, // ₹45,000
                transactionDate = now - (18 * dayMs),
                referenceNumber = "INV-2026-101",
                paymentMode = PaymentMode.CREDIT.name,
                notes = "Havells 2.5mm copper wires 10 bundles"
            )
        )
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = rajTradersId,
                accountId = upiAccId,
                type = TransactionType.GOT.name,
                amountPaise = 2000000L, // ₹20,000
                transactionDate = now - (2 * dayMs),
                referenceNumber = "UPI/6234129841",
                paymentMode = PaymentMode.UPI.name,
                notes = "Part payment via GPay QR"
            )
        )

        // 2. Mehta Hardware: Purchase ₹60,000, Paid ₹35,000 -> Net ₹25,000 Payable (Dena)
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = mehtaHardwareId,
                accountId = bankAccId,
                type = TransactionType.PURCHASE.name,
                amountPaise = 6000000L, // ₹60,000
                transactionDate = now - (35 * dayMs),
                referenceNumber = "BILL-8821",
                paymentMode = PaymentMode.CREDIT.name,
                notes = "Anchor Roma modular switch plates & MCBs"
            )
        )
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = mehtaHardwareId,
                accountId = bankAccId,
                type = TransactionType.GAVE.name,
                amountPaise = 3500000L, // ₹35,000 paid to supplier
                transactionDate = now - (5 * dayMs),
                referenceNumber = "NEFT-HDFC98214",
                paymentMode = PaymentMode.BANK_TRANSFER.name,
                notes = "NEFT payment against Bill 8821"
            )
        )

        // 3. Kumar Electricals (Overdue 90+ days): Gave ₹38,000
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = kumarElectId,
                accountId = cashAccId,
                type = TransactionType.GAVE.name,
                amountPaise = 3800000L, // ₹38,000
                transactionDate = now - (95 * dayMs),
                referenceNumber = "INV-2026-042",
                paymentMode = PaymentMode.CREDIT.name,
                notes = "Industrial panel board & meters"
            )
        )

        // 4. Neha Services: Credit given ₹18,500
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = nehaServicesId,
                accountId = upiAccId,
                type = TransactionType.GAVE.name,
                amountPaise = 1850000L, // ₹18,500
                transactionDate = now - (3 * dayMs),
                referenceNumber = "INV-2026-118",
                paymentMode = PaymentMode.CREDIT.name,
                notes = "Philips ceiling panel lights 50 pcs"
            )
        )

        // 5. Verma Builders: Credit given ₹82,000 (Overdue)
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                partyId = vermaBuildersId,
                accountId = cashAccId,
                type = TransactionType.GAVE.name,
                amountPaise = 8200000L, // ₹82,000
                transactionDate = now - (105 * dayMs),
                referenceNumber = "INV-2026-015",
                paymentMode = PaymentMode.CREDIT.name,
                notes = "Complete building wiring materials Phase 1"
            )
        )

        // 6. Direct Expenses
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                accountId = bankAccId,
                type = TransactionType.EXPENSE.name,
                amountPaise = 1800000L, // ₹18,000
                transactionDate = now - (10 * dayMs),
                paymentMode = PaymentMode.BANK_TRANSFER.name,
                notes = "Shop monthly rent Chandni Chowk"
            )
        )
        database.transactionDao().insertTransaction(
            TransactionEntity(
                businessId = businessId,
                accountId = cashAccId,
                type = TransactionType.EXPENSE.name,
                amountPaise = 240000L, // ₹2,400
                transactionDate = now - (1 * dayMs),
                paymentMode = PaymentMode.CASH.name,
                notes = "BSES Commercial Electricity Bill"
            )
        )
    }
}
