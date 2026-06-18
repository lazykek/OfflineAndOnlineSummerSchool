//
//  SessionStore.swift
//  SummerSchoolProject
//

import SwiftUI
import Combine

@MainActor
final class SessionStore: ObservableObject {
    static let shared = SessionStore()

    @Published private(set) var currentUser: String? = nil

    private let userDefaultsKey = "session.currentUser"

    private init() {
        currentUser = UserDefaults.standard.string(forKey: userDefaultsKey)
    }

    // MARK: - Login / Logout

    func login(as name: String) {
        currentUser = name
        UserDefaults.standard.set(name, forKey: userDefaultsKey)
    }

    func logout() {
        currentUser = nil
        UserDefaults.standard.removeObject(forKey: userDefaultsKey)
        CacheManager.shared.clearAll()
        TicketRepository.shared.clearLocal()
        OutboxStore.shared.clearAll()
    }
}
