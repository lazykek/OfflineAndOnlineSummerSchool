//
//  KeychainStore.swift
//  SummerSchoolProject
//

import Foundation
import Security

// MARK: - KeychainError

enum KeychainError: LocalizedError {
    case duplicateItem
    case itemNotFound
    case authFailed
    case unexpectedStatus(OSStatus)

    var errorDescription: String? {
        switch self {
            case .duplicateItem:           return "Keychain: элемент уже существует."
            case .itemNotFound:            return "Keychain: элемент не найден."
            case .authFailed:              return "Keychain: ошибка авторизации."
            case .unexpectedStatus(let s): return "Keychain: OSStatus \(s)."
        }
    }
}

// MARK: - KeychainStore

final class KeychainStore: @unchecked Sendable {
    static let shared = KeychainStore()

    private let service: String

    init(service: String = Bundle.main.bundleIdentifier ?? "app.keychain") {
        self.service = service
    }

    // MARK: - Data API

    func save(_ data: Data, account: String) throws {
        let query = baseQuery(account: account)
        let attributes: [CFString: Any] = [
            kSecValueData: data,
            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        let updateStatus = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        switch updateStatus {
            case errSecSuccess:      return
            case errSecItemNotFound: break
            default: throw KeychainError.unexpectedStatus(updateStatus)
        }

        var addQuery = baseQuery(account: account)
        addQuery[kSecValueData] = data
        addQuery[kSecAttrAccessible] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly

        let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
        switch addStatus {
            case errSecSuccess:       return
            case errSecDuplicateItem: throw KeychainError.duplicateItem
            default:                  throw KeychainError.unexpectedStatus(addStatus)
        }
    }

    func read(account: String) throws -> Data? {
        var query = baseQuery(account: account)
        query[kSecReturnData] = true
        query[kSecMatchLimit] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        switch status {
            case errSecSuccess:      return result as? Data
            case errSecItemNotFound: return nil
            case errSecAuthFailed:   throw KeychainError.authFailed
            default:                 throw KeychainError.unexpectedStatus(status)
        }
    }

    func delete(account: String) throws {
        let status = SecItemDelete(baseQuery(account: account) as CFDictionary)
        switch status {
            case errSecSuccess, errSecItemNotFound: return
            default: throw KeychainError.unexpectedStatus(status)
        }
    }

    // MARK: - String Convenience

    func save(_ string: String, account: String) throws {
        guard let data = string.data(using: .utf8) else { return }
        try save(data, account: account)
    }

    func readString(account: String) throws -> String? {
        guard let data = try read(account: account) else { return nil }
        return String(data: data, encoding: .utf8)
    }

    // MARK: - Private

    private func baseQuery(account: String) -> [CFString: Any] {
        [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: account
        ]
    }
}
