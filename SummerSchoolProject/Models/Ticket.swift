//
//  Ticket.swift
//  SummerSchoolProject
//

import Foundation

struct Ticket {
    let passengerName: String
    let flightNumber: String
    let seat: String
    let gate: String

    var qrPayload: String {
        let dict: [String: String] = [
            "passenger": passengerName,
            "flight": flightNumber,
            "seat": seat,
            "gate": gate
        ]
        guard
            let data = try? JSONSerialization.data(withJSONObject: dict),
            let json = String(data: data, encoding: .utf8)
        else {
            return "\(flightNumber)|\(seat)"
        }
        return json
    }

    init(user: RemoteUser) {
        self.passengerName = user.name
        self.flightNumber = "SS-\(String(format: "%03d", user.id * 137 % 1000))"
        self.seat = "\(user.id * 3 % 30 + 1)\(["A", "B", "C", "D"][user.id % 4])"
        self.gate = "\(["A", "B", "C"][user.id % 3])\(user.id % 20 + 1)"
    }
}
