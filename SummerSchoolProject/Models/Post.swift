//
//  Post.swift
//  SummerSchoolProject
//

import Foundation

struct Post: Decodable, Identifiable {
    let id: Int
    let title: String
    let body: String
}
