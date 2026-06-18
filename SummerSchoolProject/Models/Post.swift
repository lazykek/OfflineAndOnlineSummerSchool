//
//  Post.swift
//  SummerSchoolProject
//

import Foundation

struct Post: Decodable, Identifiable {
    let id: Int
    let title: String
    let body: String

    var imageURL: URL? {
        URL(string: "https://picsum.photos/seed/\(id)/200/120")
    }
}
