//
//  SummerSchoolProjectApp.swift
//  SummerSchoolProject
//

import SwiftUI

@main
struct SummerSchoolProjectApp: App {
    @StateObject private var session = SessionStore.shared

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(session)
        }
    }
}
