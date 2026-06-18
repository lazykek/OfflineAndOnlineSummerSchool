//
//  FeedViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var state: LoadState<[Post]> = .idle
    @Published var isOffline = false

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        if case .loaded = state {
        } else {
            state = .loading
        }

        do {
            let result: Fetched<[Post]> = try await client.get(.posts)
            isOffline = result.isFromCache
            state = .loaded(result.value)
        } catch is CancellationError {
            return
        } catch {
            isOffline = false
            state = .failed(error)
        }
    }
}
