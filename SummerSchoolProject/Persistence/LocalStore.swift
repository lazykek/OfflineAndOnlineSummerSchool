//
//  LocalStore.swift
//  SummerSchoolProject
//
//  COMMIT 4 — Generic persistent store: Codable → JSON-файл в Application Support.
//
//  📁 СЛАЙД: Папки песочницы iOS
//  ┌──────────────────────────────────────────────────────────────────┐
//  │ Documents/              — пользовательские файлы, виден в Finder │
//  │ Library/Caches/         — URLCache, картинки: OS МОЖЕТ удалить   │
//  │ Library/Application Support/ ← МЫ ЗДЕСЬ                         │
//  │                         — бэкапируется в iCloud, OS НЕ трогает   │
//  │ tmp/                    — временные файлы, OS чистит произвольно  │
//  └──────────────────────────────────────────────────────────────────┘
//
//  Почему Application Support, а не Caches?
//  • Caches — для ПРОИЗВОДНЫХ данных (можно пересчитать/перекачать).
//  • Application Support — для ПОЛЬЗОВАТЕЛЬСКИХ данных, которые сложно
//    восстановить без сети. Билет — именно такой случай:
//    OS вычищает Caches под давлением диска → пассажир без QR на стойке.
//

import Foundation

/// Generic thread-safe file-backed store for any Codable value.
/// Каждое значение — отдельный JSON-файл в `Library/Application Support/<bundle-id>/`.
final class LocalStore: @unchecked Sendable {
    static let shared = LocalStore()

    // MARK: - Private

    /// Корневая директория: Library/Application Support/<bundle-id>/
    private let baseURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    /// Защита файловых операций от конкурентного доступа.
    private let queue = DispatchQueue(label: "app.localStore", qos: .utility)

    private init() {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!

        let bundleID = Bundle.main.bundleIdentifier ?? "app"
        baseURL = appSupport.appendingPathComponent(bundleID, isDirectory: true)

        // Создаём директорию при первом запуске (noop если уже есть).
        try? FileManager.default.createDirectory(
            at: baseURL,
            withIntermediateDirectories: true
        )
        print("[LocalStore] 📁 \(baseURL.path)")
    }

    // MARK: - Public API

    /// Синхронно записать Codable-значение в `<baseURL>/<key>.json`.
    func save<T: Encodable>(_ value: T, forKey key: String) {
        queue.sync {
            guard let data = try? encoder.encode(value) else { return }
            try? data.write(to: fileURL(key), options: .atomic)
        }
    }

    /// Синхронно прочитать Codable-значение из `<baseURL>/<key>.json`.
    /// Возвращает nil, если файл не существует или не декодируется.
    func load<T: Decodable>(forKey key: String) -> T? {
        queue.sync {
            guard
                let data = try? Data(contentsOf: fileURL(key)),
                let value = try? decoder.decode(T.self, from: data)
            else { return nil }
            return value
        }
    }

    /// Удалить файл по ключу. Игнорирует отсутствие файла.
    func remove(forKey key: String) {
        queue.sync {
            try? FileManager.default.removeItem(at: fileURL(key))
        }
    }

    /// Полный путь к файлу — для отладки и слайдов.
    func filePath(forKey key: String) -> String {
        fileURL(key).path
    }

    // MARK: - Private

    private func fileURL(_ key: String) -> URL {
        baseURL.appendingPathComponent("\(key).json")
    }
}
