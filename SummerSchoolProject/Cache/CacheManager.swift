//
//  CacheManager.swift
//  SummerSchoolProject
//

import Foundation

// MARK: - Cache data source

enum DataSource: Equatable {
    case network
    case staleCache(age: TimeInterval)
    case offlineCache
}

// MARK: - CacheManager

final class CacheManager: @unchecked Sendable {
    static let shared = CacheManager()

    static let cacheSchemaVersion = 1
    static let cacheTTL: TimeInterval = 60

    private let versionKey = "cache.schemaVersion"
    private let timestampKey = "cache.timestamps.v1"

    let urlCache: URLCache = URLCache(
        memoryCapacity: 16 * 1024 * 1024,
        diskCapacity: 128 * 1024 * 1024,
        diskPath: "api-cache"
    )

    private init() {
        validateSchemaVersion()
    }

    private func validateSchemaVersion() {
        let stored = UserDefaults.standard.integer(forKey: versionKey)
        if stored != CacheManager.cacheSchemaVersion {
            clearAll()
            UserDefaults.standard.set(CacheManager.cacheSchemaVersion, forKey: versionKey)
        }
    }

    // MARK: - TTL metadata

    func saveTimestamp(for key: String) {
        var timestamps = storedTimestamps()
        timestamps[key] = Date()
        if let data = try? JSONEncoder().encode(timestamps) {
            UserDefaults.standard.set(data, forKey: timestampKey)
        }
    }

    func dataSource(for key: String, isNetworkAvailable: Bool) -> DataSource {
        guard let savedAt = storedTimestamps()[key] else {
            return isNetworkAvailable ? .staleCache(age: .infinity) : .offlineCache
        }
        let age = Date().timeIntervalSince(savedAt)
        if !isNetworkAvailable {
            return .offlineCache
        }
        if age <= CacheManager.cacheTTL {
            return .offlineCache
        }
        return .staleCache(age: age)
    }

    // MARK: - Logout cleanup

    func clearAll() {
        urlCache.removeAllCachedResponses()
        UserDefaults.standard.removeObject(forKey: timestampKey)
        ImageLoader.shared.clearCache()
    }

    // MARK: - Private helpers

    private func storedTimestamps() -> [String: Date] {
        guard
            let data = UserDefaults.standard.data(forKey: timestampKey),
            let dict = try? JSONDecoder().decode([String: Date].self, from: data)
        else { return [:] }
        return dict
    }
}
