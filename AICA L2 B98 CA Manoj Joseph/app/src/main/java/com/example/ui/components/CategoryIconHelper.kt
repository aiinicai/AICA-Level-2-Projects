package com.example.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalance
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.CardGiftcard
import androidx.compose.material.icons.filled.Category
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.DirectionsBus
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.Flight
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocalCafe
import androidx.compose.material.icons.filled.LocalGasStation
import androidx.compose.material.icons.filled.MedicalServices
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Paid
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Pets
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Redeem
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.Savings
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Sell
import androidx.compose.material.icons.filled.ShoppingBag
import androidx.compose.material.icons.filled.Spa
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.Work
import androidx.compose.ui.graphics.vector.ImageVector

data class CategoryIconItem(
    val id: String,
    val label: String,
    val icon: ImageVector
)

object CategoryIconHelper {
    val categoryIcons: List<CategoryIconItem> = listOf(
        CategoryIconItem("restaurant", "Food & Dining", Icons.Default.Restaurant),
        CategoryIconItem("local_cafe", "Coffee & Snacks", Icons.Default.LocalCafe),
        CategoryIconItem("directions_bus", "Transport", Icons.Default.DirectionsBus),
        CategoryIconItem("local_gas_station", "Fuel", Icons.Default.LocalGasStation),
        CategoryIconItem("school", "Education", Icons.Default.School),
        CategoryIconItem("shopping_bag", "Shopping", Icons.Default.ShoppingBag),
        CategoryIconItem("sports_esports", "Gaming", Icons.Default.SportsEsports),
        CategoryIconItem("fitness_center", "Fitness & Gym", Icons.Default.FitnessCenter),
        CategoryIconItem("spa", "Personal Care", Icons.Default.Spa),
        CategoryIconItem("medical_services", "Health & Meds", Icons.Default.MedicalServices),
        CategoryIconItem("card_giftcard", "Gifts", Icons.Default.CardGiftcard),
        CategoryIconItem("savings", "Savings", Icons.Default.Savings),
        CategoryIconItem("account_balance_wallet", "Wallet", Icons.Default.AccountBalanceWallet),
        CategoryIconItem("account_balance", "Bank / Interest", Icons.Default.AccountBalance),
        CategoryIconItem("redeem", "Gifts Received", Icons.Default.Redeem),
        CategoryIconItem("work", "Salary / Work", Icons.Default.Work),
        CategoryIconItem("computer", "Tech / Freelance", Icons.Default.Computer),
        CategoryIconItem("paid", "Cash / Income", Icons.Default.Paid),
        CategoryIconItem("payments", "Payments", Icons.Default.Payments),
        CategoryIconItem("replay", "Refunds", Icons.Default.Replay),
        CategoryIconItem("trending_up", "Investments", Icons.Default.TrendingUp),
        CategoryIconItem("home", "Rent / Home", Icons.Default.Home),
        CategoryIconItem("pets", "Pets", Icons.Default.Pets),
        CategoryIconItem("movie", "Entertainment", Icons.Default.Movie),
        CategoryIconItem("flight", "Travel", Icons.Default.Flight),
        CategoryIconItem("sell", "Resale / Trade", Icons.Default.Sell),
        CategoryIconItem("phone_android", "Phone / Bills", Icons.Default.PhoneAndroid),
        CategoryIconItem("wifi", "Internet", Icons.Default.Wifi),
        CategoryIconItem("more_horiz", "Other", Icons.Default.MoreHoriz),
        CategoryIconItem("category", "General", Icons.Default.Category)
    )

    val categoryColors: List<String> = listOf(
        "#10B981", // Emerald
        "#059669", // Dark Green
        "#3B82F6", // Blue
        "#6366F1", // Indigo
        "#8B5CF6", // Purple
        "#EC4899", // Pink
        "#F97316", // Orange
        "#EAB308", // Yellow
        "#06B6D4", // Cyan
        "#14B8A6", // Teal
        "#EF4444", // Red
        "#6B7280"  // Gray
    )

    fun getIcon(name: String): ImageVector {
        return categoryIcons.find { it.id == name }?.icon ?: Icons.Default.Category
    }
}
