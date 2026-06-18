//
//  OutboxProcessor.swift
//  SummerSchoolProject
//

import Foundation
import Combine

// MARK: - POST payload

private struct LikePayload: Encodable {
    let postId: Int
    let action: String
    let clientID: String
}

private struct PostResponse: Decodable { let id: Int }

// MARK: - OutboxProcessor

@MainActor
final class OutboxProcessor: ObservableObject {
    static let shared = OutboxProcessor()

    private let outbox: OutboxStore
    private let api: APIClient
    private let monitor: NetworkMonitor
    private var cancellables = Set<AnyCancellable>()
    private var isProcessing = false

    init(outbox: OutboxStore = .shared,
         api: APIClient = .shared,
         monitor: NetworkMonitor = .shared) {
        self.outbox = outbox
        self.api = api
        self.monitor = monitor
    }

    // MARK: - Start

    func start() {
        monitor.$isOnline
            .filter { $0 }
            .sink { [weak self] _ in
                print("[OutboxProcessor] 🌐 Network restored — syncing…")
                Task { await self?.processQueue() }
            }
            .store(in: &cancellables)

        if monitor.isOnline {
            Task { await processQueue() }
        }
    }

    // MARK: - Enqueue

    func enqueue(_ action: OutboxAction) {
        outbox.enqueue(action)
        if monitor.isOnline { Task { await processQueue() } }
    }

    // MARK: - Queue processing

    func processQueue() async {
        guard !isProcessing else { return }
        isProcessing = true
        defer { isProcessing = false }

        let pending = outbox.allPending
        guard !pending.isEmpty else { return }
        print("[OutboxProcessor] 🚀 Processing \(pending.count) item(s)…")

        for item in pending { await send(item) }
    }

    // MARK: - Private

    private func send(_ item: OutboxItem) async {
        if item.retryCount > 0 {
            let delay = pow(2.0, Double(item.retryCount - 1))
            if Date().timeIntervalSince(item.createdAt) < delay {
                print("[OutboxProcessor] ⏳ Backoff for \(item.clientID)")
                return
            }
        }

        outbox.markInFlight(item.clientID)

        do {
            let payload = LikePayload(
                postId: postID(from: item.action),
                action: "like",
                clientID: item.clientID.uuidString
            )
            let _: PostResponse = try await api.post(
                .posts,
                body: payload,
                idempotencyKey: item.clientID.uuidString
            )
            outbox.markSent(item.clientID)
        } catch {
            outbox.markFailed(item.clientID)
            print("[OutboxProcessor] ❌ \(item.clientID): \(error.localizedDescription)")
        }
    }

    private func postID(from action: OutboxAction) -> Int {
        switch action { case .likePost(let id): return id }
    }
}
