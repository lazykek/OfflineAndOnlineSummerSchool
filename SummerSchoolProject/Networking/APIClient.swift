//
//  APIClient.swift
//  SummerSchoolProject
//

import Foundation

enum Endpoint {
    static let baseURL = URL(string: "https://jsonplaceholder.typicode.com")!

    case posts
    case user(id: Int)

    var url: URL {
        switch self {
            case .posts:
                return Endpoint.baseURL.appendingPathComponent("posts")
            case .user(let id):
                return Endpoint.baseURL.appendingPathComponent("users/\(id)")
        }
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case statusCode(Int)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
            case .invalidResponse:
                "Некорректный ответ сервера."
            case .statusCode(let code):
                "Сервер вернул ошибку (код \(code))."
            case .decoding:
                "Не удалось обработать данные."
            case .transport:
                "Не удалось загрузить. Проверьте соединение."
        }
    }
}

struct Fetched<Value> {
    let value: Value
    let isFromCache: Bool
}

nonisolated struct APIClient {
    static let requestTimeout: TimeInterval = 5

    static let shared = APIClient()

    private let session: URLSession
    private let cache: URLCache
    private let decoder: JSONDecoder

    init() {
        let cache = URLCache(
            memoryCapacity: 16 * 1024 * 1024,
            diskCapacity: 128 * 1024 * 1024,
            diskPath: "api-cache"
        )

        let config = URLSessionConfiguration.default
        config.urlCache = cache
        config.requestCachePolicy = .useProtocolCachePolicy
        config.timeoutIntervalForRequest  = APIClient.requestTimeout
        config.timeoutIntervalForResource = APIClient.requestTimeout

        self.cache = cache
        self.session = URLSession(configuration: config)
        self.decoder = JSONDecoder()
    }

    func get<T: Decodable>(_ endpoint: Endpoint) async throws -> Fetched<T> {
        let request = URLRequest(url: endpoint.url)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is CancellationError {
            throw CancellationError()
        } catch let urlError as URLError where urlError.code == .cancelled {
            throw CancellationError()
        } catch {
            if let cached = cache.cachedResponse(for: request) {
                return Fetched(value: try decode(cached.data), isFromCache: true)
            }
            throw APIError.transport(error)
        }

        try validate(response)
        return Fetched(value: try decode(data), isFromCache: false)
    }

    // MARK: - Helpers

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.statusCode(http.statusCode)
        }
    }

    private func decode<T: Decodable>(_ data: Data) throws -> T {
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}
