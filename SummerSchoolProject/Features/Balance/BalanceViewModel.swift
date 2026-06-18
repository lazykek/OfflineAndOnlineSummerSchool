//
//  BalanceViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

@MainActor
final class BalanceViewModel: ObservableObject {
    @Published var state: LoadState<Balance> = .idle

    private let client: APIClient

    init(client: APIClient = .shared) {
        self.client = client
    }

    func load() async {
        state = .loading
        do {
            let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
            state = .loaded(Balance(user: result.value))
        } catch {
            state = .failed(error)
        }
    }
}
