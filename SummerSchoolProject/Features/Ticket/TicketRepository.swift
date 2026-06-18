//
//  TicketRepository.swift
//  SummerSchoolProject
//

import Foundation

// MARK: - TicketRepository

final class TicketRepository: @unchecked Sendable {
    static let shared = TicketRepository()

    // MARK: - Private

    private let store: LocalStore
    private let client: APIClient

    private let ticketKey   = "ticket"
    private let syncedAtKey = "ticket.lastSyncedAt"

    init(store: LocalStore = .shared, client: APIClient = .shared) {
        self.store  = store
        self.client = client
    }

    // MARK: - Public API

    func loadLocal() -> Ticket? {
        store.load(forKey: ticketKey)
    }

    var lastSyncedAt: Date? {
        store.load(forKey: syncedAtKey)
    }

    var localFilePath: String {
        store.filePath(forKey: ticketKey)
    }

    @discardableResult
    func refreshFromNetwork() async throws -> Ticket {
        let result: Fetched<RemoteUser> = try await client.get(.user(id: 1))
        let ticket = Ticket(user: result.value)

        store.save(ticket, forKey: ticketKey)
        store.save(Date(), forKey: syncedAtKey)
        print("[TicketRepository] ✅ Synced from network, saved to Application Support.")
        return ticket
    }

    func clearLocal() {
        store.remove(forKey: ticketKey)
        store.remove(forKey: syncedAtKey)
        print("[TicketRepository] 🗑 Local ticket cleared.")
    }
}
