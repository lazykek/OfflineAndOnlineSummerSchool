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

nonisolated struct APIClient {
    static let requestTimeout: TimeInterval = 5

    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = APIClient.requestTimeout
        config.timeoutIntervalForResource = APIClient.requestTimeout
        self.session = URLSession(configuration: config)
        self.decoder = JSONDecoder()
    }

    func get<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(from: endpoint.url)
        } catch is CancellationError {
            throw CancellationError()
        } catch let urlError as URLError where urlError.code == .cancelled {
            throw CancellationError()
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.statusCode(http.statusCode)
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}
