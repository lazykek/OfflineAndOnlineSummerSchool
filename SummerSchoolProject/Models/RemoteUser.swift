//
//  RemoteUser.swift
//  SummerSchoolProject
//

import Foundation

struct RemoteUser: Decodable {
    let id: Int
    let name: String
    let username: String
    let email: String
    let phone: String

    struct Company: Decodable {
        let name: String
    }
    let company: Company

    struct Address: Decodable {
        let city: String
    }
    let address: Address
}
