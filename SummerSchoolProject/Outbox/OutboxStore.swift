//
//  OutboxStore.swift
//  SummerSchoolProject
//

import Foundation
import Combine

@MainActor
final class OutboxStore: ObservableObject {
    static let shared = OutboxStore()

    @Published private(set) var items: [OutboxItem] = []

    private let store: LocalStore
    private let storeKey = "outbox"

    init(store: LocalStore = .shared) {
        self.store = store
        self.items = store.load(forKey: storeKey) ?? []
        print("[OutboxStore] 📬 Loaded \(items.count) item(s) from disk.")
    }

    // MARK: - Public API

    func enqueue(_ action: OutboxAction) {
        let item = OutboxItem(action: action)
        items.append(item)
        persist()
        print("[OutboxStore] ➕ Enqueued \(item.clientID)")
    }

    var allPending: [OutboxItem] { items.filter { $0.status == .pending } }

    var pendingCount: Int { allPending.count }

    func markInFlight(_ id: UUID) {
        update(id) { $0.status = .inFlight }
    }

    func markSent(_ id: UUID) {
        items.removeAll { $0.clientID == id }
        persist()
        print("[OutboxStore] ✅ Sent & removed: \(id)")
    }

    func markFailed(_ id: UUID, maxRetries: Int = 5) {
        update(id) { item in
            item.retryCount += 1
            item.status = item.retryCount >= maxRetries ? .failed : .pending
        }
        persist()
    }

    func clearAll() {
        items.removeAll()
        store.remove(forKey: storeKey)
        print("[OutboxStore] 🗑 Queue cleared (logout).")
    }

    // MARK: - Private

    private func update(_ id: UUID, mutation: (inout OutboxItem) -> Void) {
        guard let idx = items.firstIndex(where: { $0.clientID == id }) else { return }
        mutation(&items[idx])
        persist()
    }

    private func persist() {
        store.save(items, forKey: storeKey)
    }
}
