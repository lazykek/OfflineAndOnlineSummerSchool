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
    @Published private(set) var accessToken: String? = nil

    private let userDefaultsKey = "session.currentUser"
    private let tokenKeychainAccount = "accessToken"
    private let keychain = KeychainStore.shared

    private init() {
        currentUser = UserDefaults.standard.string(forKey: userDefaultsKey)
        accessToken = try? keychain.readString(account: tokenKeychainAccount)

        if accessToken != nil && currentUser == nil {
            try? keychain.delete(account: tokenKeychainAccount)
            accessToken = nil
        }

        TokenHolder.shared.token = accessToken
    }

    // MARK: - Login / Logout

    func login(as name: String) {
        let token = "demo-token-\(UUID().uuidString)"

        do {
            try keychain.save(token, account: tokenKeychainAccount)
        } catch {
            print("[SessionStore] ⚠️ Keychain save failed: \(error)")
        }

        currentUser = name
        accessToken = token
        UserDefaults.standard.set(name, forKey: userDefaultsKey)
        TokenHolder.shared.token = token
    }

    func logout() {
        do {
            try keychain.delete(account: tokenKeychainAccount)
        } catch {
            print("[SessionStore] ⚠️ Keychain delete failed: \(error)")
        }

        currentUser = nil
        accessToken = nil
        TokenHolder.shared.token = nil
        UserDefaults.standard.removeObject(forKey: userDefaultsKey)
        CacheManager.shared.clearAll()
        TicketRepository.shared.clearLocal()
        OutboxStore.shared.clearAll()
    }
}
