//
//  LocalStore.swift
//  SummerSchoolProject
//

import Foundation

final class LocalStore: @unchecked Sendable {
    static let shared = LocalStore()

    // MARK: - Private

    private let baseURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private let queue = DispatchQueue(label: "app.localStore", qos: .utility)

    private init() {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!

        let bundleID = Bundle.main.bundleIdentifier ?? "app"
        baseURL = appSupport.appendingPathComponent(bundleID, isDirectory: true)

        try? FileManager.default.createDirectory(
            at: baseURL,
            withIntermediateDirectories: true
        )
        print("[LocalStore] 📁 \(baseURL.path)")
    }

    // MARK: - Public API

    func save<T: Encodable>(_ value: T, forKey key: String) {
        queue.sync {
            guard let data = try? encoder.encode(value) else { return }
            try? data.write(to: fileURL(key), options: .atomic)
        }
    }

    func load<T: Decodable>(forKey key: String) -> T? {
        queue.sync {
            guard
                let data = try? Data(contentsOf: fileURL(key)),
                let value = try? decoder.decode(T.self, from: data)
            else { return nil }
            return value
        }
    }

    func remove(forKey key: String) {
        queue.sync {
            try? FileManager.default.removeItem(at: fileURL(key))
        }
    }

    func filePath(forKey key: String) -> String {
        fileURL(key).path
    }

    // MARK: - Private

    private func fileURL(_ key: String) -> URL {
        baseURL.appendingPathComponent("\(key).json")
    }
}
