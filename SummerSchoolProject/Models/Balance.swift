//
//  Balance.swift
//  SummerSchoolProject
//

import Foundation

struct Balance {
    let holderName: String
    let email: String
    let city: String
    let amount: Decimal
    let currency: String

    var formattedAmount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = currency
        return formatter.string(from: amount as NSDecimalNumber) ?? "\(amount) \(currency)"
    }

    init(user: RemoteUser) {
        self.holderName = user.name
        self.email = user.email
        self.city = user.address.city
        self.amount = Decimal(user.id * 1234 + 567) / 100
        self.currency = "USD"
    }
}
