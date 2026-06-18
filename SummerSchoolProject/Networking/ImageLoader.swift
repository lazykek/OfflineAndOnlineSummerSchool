//
//  ImageLoader.swift
//  SummerSchoolProject
//

import UIKit

final class ImageLoader {
    static let shared = ImageLoader()

    private let memory = NSCache<NSURL, UIImage>()
    private let session: URLSession

    private init() {
        let cache = URLCache(
            memoryCapacity: 8 * 1024 * 1024,
            diskCapacity: 256 * 1024 * 1024,
            diskPath: "image-cache"
        )
        let config = URLSessionConfiguration.default
        config.urlCache = cache
        config.requestCachePolicy = .useProtocolCachePolicy
        self.session = URLSession(configuration: config)
    }

    func image(for url: URL) async throws -> UIImage {
        if let cached = memory.object(forKey: url as NSURL) {
            return cached
        }

        let request = URLRequest(url: url)
        do {
            let (data, _) = try await session.data(for: request)
            return try store(data, for: url)
        } catch {
            if let cached = session.configuration.urlCache?.cachedResponse(for: request),
               let image = UIImage(data: cached.data) {
                memory.setObject(image, forKey: url as NSURL)
                return image
            }
            throw error
        }
    }

    private func store(_ data: Data, for url: URL) throws -> UIImage {
        guard let image = UIImage(data: data) else {
            throw URLError(.cannotDecodeContentData)
        }
        memory.setObject(image, forKey: url as NSURL)
        return image
    }
}
