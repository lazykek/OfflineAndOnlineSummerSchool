//
//  FeedViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var state: LoadState<[Post]> = .idle
    @Published var dataSource: DataSource = .network

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        if case .idle = state {
            if let cached: Fetched<[Post]> = client.getCachedIfAvailable(.posts) {
                dataSource = cached.dataSource
                state = .loaded(cached.value)
            } else {
                state = .loading
            }
        }

        do {
            let result: Fetched<[Post]> = try await client.get(.posts)
            dataSource = result.dataSource
            state = .loaded(result.value)
        } catch is CancellationError {
            return
        } catch {
            if case .loaded = state { }
            else { state = .failed(error) }
        }
    }
}
