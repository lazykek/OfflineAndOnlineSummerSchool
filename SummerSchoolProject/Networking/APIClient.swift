//
//  APIClient.swift
//  SummerSchoolProject
//

import Foundation

// MARK: - TokenHolder

final class TokenHolder: @unchecked Sendable {
    static let shared = TokenHolder()
    nonisolated(unsafe) var token: String? = nil
    private init() {}
}

// MARK: - Endpoints

enum Endpoint {
    static let baseURL = URL(string: "https://jsonplaceholder.typicode.com")!

    case posts
    case user(id: Int)

    nonisolated var url: URL {
        switch self {
        case .posts: return Endpoint.baseURL.appendingPathComponent("posts")
        case .user(let id): return Endpoint.baseURL.appendingPathComponent("users/\(id)")
        }
    }

    nonisolated var cacheKey: String {
        switch self {
        case .posts: return "endpoint.posts"
        case .user(let id): return "endpoint.user.\(id)"
        }
    }
}

// MARK: - Errors

enum APIError: LocalizedError {
    case invalidResponse
    case statusCode(Int)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Некорректный ответ сервера."
        case .statusCode(let c): return "Сервер вернул ошибку (код \(c))."
        case .decoding: return "Не удалось обработать данные."
        case .transport: return "Не удалось загрузить. Проверьте соединение."
        }
    }
}

// MARK: - Fetched<Value>

struct Fetched<Value> {
    let value: Value
    let dataSource: DataSource
    var isFromCache: Bool { dataSource != .network }
}

// MARK: - APIClient

nonisolated struct APIClient {
    static let requestTimeout: TimeInterval = 5

    static let shared = APIClient()

    private let cache: URLCache
    private let session: URLSession
    private let decoder: JSONDecoder
    private let cacheManager: CacheManager

    init() {
        cacheManager = CacheManager.shared
        cache = cacheManager.urlCache

        let config = URLSessionConfiguration.default
        config.urlCache = cache
        config.requestCachePolicy = .useProtocolCachePolicy
        config.timeoutIntervalForRequest = APIClient.requestTimeout
        config.timeoutIntervalForResource = APIClient.requestTimeout

        session = URLSession(configuration: config)
        decoder = JSONDecoder()
    }

    // MARK: - Public API

    func getCachedIfAvailable<T: Decodable>(_ endpoint: Endpoint) -> Fetched<T>? {
        let request = authorizedRequest(for: endpoint.url)
        guard
            let cached = cache.cachedResponse(for: request),
            let value = try? decode(cached.data) as T
        else { return nil }

        let source = cacheManager.dataSource(
            for: endpoint.cacheKey,
            isNetworkAvailable: true
        )
        return Fetched(value: value, dataSource: source)
    }

    func get<T: Decodable>(_ endpoint: Endpoint) async throws -> Fetched<T> {
        let request = authorizedRequest(for: endpoint.url)

        do {
            let (rawData, response) = try await session.data(for: request)
            try validate(response)
            cacheManager.saveTimestamp(for: endpoint.cacheKey)
            return Fetched(value: try decode(rawData), dataSource: .network)
        } catch is CancellationError {
            throw CancellationError()
        } catch let urlError as URLError where urlError.code == .cancelled {
            throw CancellationError()
        } catch let error as APIError {
            throw error
        } catch {
            if let cached = cache.cachedResponse(for: request),
               let value = try? decode(cached.data) as T {
                let source = cacheManager.dataSource(
                    for: endpoint.cacheKey,
                    isNetworkAvailable: false
                )
                return Fetched(value: value, dataSource: source)
            }
            throw APIError.transport(error)
        }
    }

    @discardableResult
    func post<Body: Encodable, Response: Decodable>(
        _ endpoint: Endpoint,
        body: Body,
        idempotencyKey: String
    ) async throws -> Response {
        var request = authorizedRequest(for: endpoint.url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(idempotencyKey, forHTTPHeaderField: "Idempotency-Key")
        request.httpBody = try JSONEncoder().encode(body)

        do {
            let (data, response) = try await session.data(for: request)
            try validate(response)
            return try decode(data)
        } catch let e as APIError { throw e }
        catch { throw APIError.transport(error) }
    }

    // MARK: - Helpers

    private func authorizedRequest(for url: URL) -> URLRequest {
        var request = URLRequest(url: url)
        if let token = TokenHolder.shared.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    private func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else { throw APIError.statusCode(http.statusCode) }
    }

    private func decode<T: Decodable>(_ data: Data) throws -> T {
        do { return try decoder.decode(T.self, from: data) }
        catch { throw APIError.decoding(error) }
    }
}
