//
//  FeedViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class FeedViewModel: ObservableObject {
    @Published var state: LoadState<[Post]> = .idle

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
            let posts: [Post] = try await client.get(.posts)
            state = .loaded(posts)
        } catch is CancellationError {
            return
        } catch {
            state = .failed(error)
        }
    }
}
