//
//  SummerSchoolProjectApp.swift
//  SummerSchoolProject
//

import SwiftUI

@main
struct SummerSchoolProjectApp: App {
    @StateObject private var session = SessionStore.shared
    @StateObject private var monitor = NetworkMonitor.shared
    @StateObject private var outbox = OutboxStore.shared
    @StateObject private var processor = OutboxProcessor.shared

    var body: some Scene {
        WindowGroup {
            RootTabView()
                .environmentObject(session)
                .environmentObject(monitor)
                .environmentObject(outbox)
                .environmentObject(processor)
                .task {
                    processor.start()
                }
        }
    }
}
