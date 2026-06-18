//
//  BalanceViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class BalanceViewModel: ObservableObject {
    @Published var state: LoadState<Balance> = .idle
    @Published var dataSource: DataSource = .network

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        if case .idle = state {
            if let cached: Fetched<RemoteUser> = client.getCachedIfAvailable(.user(id: 1)) {
                dataSource = cached.dataSource
                state = .loaded(Balance(user: cached.value))
            } else {
                state = .loading
            }
        }

        do {
            let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
            dataSource = result.dataSource
            state = .loaded(Balance(user: result.value))
        } catch {
            if case .loaded = state { /* keep cached data */ }
            else { state = .failed(error) }
        }
    }
}
