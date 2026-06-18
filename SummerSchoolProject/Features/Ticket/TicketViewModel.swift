//
//  TicketViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class TicketViewModel: ObservableObject {
    @Published var state: LoadState<Ticket> = .idle
    @Published var dataSource: DataSource = .network

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        if case .idle = state {
            if let cached: Fetched<RemoteUser> = client.getCachedIfAvailable(.user(id: 1)) {
                dataSource = cached.dataSource
                state = .loaded(Ticket(user: cached.value))
            } else {
                state = .loading
            }
        }

        do {
            let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
            dataSource = result.dataSource
            state = .loaded(Ticket(user: result.value))
        } catch {
            if case .loaded = state { /* keep cached data */ }
            else { state = .failed(error) }
        }
    }
}
