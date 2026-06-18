//
//  TicketViewModel.swift
//  SummerSchoolProject
//

import Combine
import Foundation

// MARK: - TicketSyncStatus

enum TicketSyncStatus: Equatable {
    case synced(at: Date)
    case offline
    case syncing
}

// MARK: - TicketViewModel

@MainActor
final class TicketViewModel: ObservableObject {
    @Published var state: LoadState<Ticket> = .idle
    @Published var syncStatus: TicketSyncStatus = .syncing

    private let repository: TicketRepository

    init(repository: TicketRepository? = nil) {
        self.repository = repository ?? .shared
    }

    func load() async {
        if let local = repository.loadLocal() {
            state = .loaded(local)
            syncStatus = .syncing
        } else {
            state = .loading
        }

        do {
            let fresh = try await repository.refreshFromNetwork()
            state = .loaded(fresh)
            syncStatus = .synced(at: repository.lastSyncedAt ?? Date())
        } catch {
            if case .loaded = state {
                syncStatus = .offline
            } else {
                state = .failed(error)
            }
        }
    }
}
