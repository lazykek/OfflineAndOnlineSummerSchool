//
//  TicketViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class TicketViewModel: ObservableObject {
    @Published var state: LoadState<Ticket> = .idle

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        state = .loading
        do {
            let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
            state = .loaded(Ticket(user: result.value))
        } catch {
            state = .failed(error)
        }
    }
}
