//
//  ImageLoader.swift
//  SummerSchoolProject
//

import UIKit
import CryptoKit

final class ImageLoader {
    static let shared = ImageLoader()

    // MARK: - Level 1: memory

    private let memory = NSCache<NSURL, UIImage>()

    // MARK: - Level 2: disk

    let diskCacheURL: URL

    // MARK: - Level 3: network

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.urlCache = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        return URLSession(configuration: config)
    }()

    private init() {
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        diskCacheURL = caches.appendingPathComponent("image-disk-cache", isDirectory: true)
        try? FileManager.default.createDirectory(at: diskCacheURL,
                                                 withIntermediateDirectories: true)
    }

    // MARK: - Public API

    func image(for url: URL) async throws -> UIImage {
        if let cached = memory.object(forKey: url as NSURL) {
            return cached
        }
        if let image = loadFromDisk(for: url) {
            memory.setObject(image, forKey: url as NSURL)
            return image
        }
        let (data, _) = try await session.data(from: url)
        guard let image = UIImage(data: data) else {
            throw URLError(.cannotDecodeContentData)
        }
        saveToDisk(data, for: url)
        memory.setObject(image, forKey: url as NSURL)
        return image
    }

    // MARK: - Cache clearance

    func clearCache() {
        memory.removeAllObjects()
        try? FileManager.default.removeItem(at: diskCacheURL)
        try? FileManager.default.createDirectory(at: diskCacheURL,
                                                 withIntermediateDirectories: true)
    }

    // MARK: - Disk helpers

    private func diskFileURL(for url: URL) -> URL {
        let digest = SHA256.hash(data: Data(url.absoluteString.utf8))
        let hex = digest.map { String(format: "%02x", $0) }.joined()
        return diskCacheURL.appendingPathComponent(hex)
    }

    private func loadFromDisk(for url: URL) -> UIImage? {
        let file = diskFileURL(for: url)
        guard let data = try? Data(contentsOf: file) else { return nil }
        return UIImage(data: data)
    }

    private func saveToDisk(_ data: Data, for url: URL) {
        let file = diskFileURL(for: url)
        try? data.write(to: file, options: .atomic)
    }
}
